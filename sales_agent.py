import os
import csv
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd
from dotenv import load_dotenv
from dialogflow_client import DialogflowClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sales_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SalesAgent:
    def __init__(self):
        self.leads_file = 'leads.csv'
        self.sessions: Dict[str, dict] = {}  # Store active sessions
        self.dialogflow_client = DialogflowClient()
        self._initialize_leads_file()
        self.follow_up_tasks = {}  # Store follow-up tasks
        self.loop = asyncio.get_event_loop()  # Get the event loop
        
    def _initialize_leads_file(self):
        """Initialize the leads.csv file if it doesn't exist"""
        if not os.path.exists(self.leads_file):
            with open(self.leads_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['lead_id', 'name', 'age', 'country', 'interest', 'status'])

    async def handle_lead(self, lead_id: str, name: str, source: str = "unknown"):
        """Handle a new lead interaction triggered by external event"""
        try:
            # Validate lead_id
            if not self._validate_lead_id(lead_id):
                raise ValueError(f"Invalid or duplicate lead_id: {lead_id}")
            
            # Create new session
            current_time = datetime.now()
            self.sessions[lead_id] = {
                'name': name,
                'status': 'pending',
                'last_interaction': current_time,
                'conversation_start': current_time,
                'responses': {},
                'source': source,
                'current_intent': None,
                'collected_params': set()  # Track collected parameters
            }
            
            # Create initial context in Dialogflow
            await self.dialogflow_client.create_context(lead_id, "initial_greeting")
            
            # Send initial message through Dialogflow
            response = await self.dialogflow_client.detect_intent(
                lead_id,
                f"Start conversation with {name}"
            )
            
            # Update current intent
            self.sessions[lead_id]['current_intent'] = response['intent']
            
            # Send the response
            await self._send_message(lead_id, response['fulfillment_text'])
            
            # Start follow-up monitoring in the background
            if lead_id not in self.follow_up_tasks:
                self.follow_up_tasks[lead_id] = self.loop.create_task(self._monitor_follow_up(lead_id))
                logger.info(f"Started follow-up monitoring for lead {lead_id}")
            
            logger.info(f"New lead session started from {source}: {lead_id} ({name})")
            
        except Exception as e:
            logger.error(f"Error handling lead {lead_id}: {str(e)}")
            raise

    async def process_response(self, lead_id: str, response: str):
        """Process a lead's response using Dialogflow"""
        if lead_id not in self.sessions:
            logger.error(f"No active session for lead {lead_id}")
            return

        session = self.sessions[lead_id]
        session['last_interaction'] = datetime.now()
        
        logger.info(f"Processing response for lead {lead_id}: {response}")
        logger.info(f"Reset follow-up flags for lead {lead_id}")

        try:
            # Handle empty responses
            if not response or response.strip() == "":
                logger.warning(f"Empty response received from lead {lead_id}")
                await self._send_message(lead_id, "I didn't catch that. Could you please respond?")
                return

            # Get intent and response from Dialogflow
            dialogflow_response = await self.dialogflow_client.detect_intent(lead_id, response)
            
            # Update current intent
            session['current_intent'] = dialogflow_response['intent']
            
            # Handle the response based on intent
            intent = dialogflow_response['intent']
            parameters = dialogflow_response['parameters']
            
            # Update session with any parameters collected
            if parameters:
                for param_name, param_value in parameters.items():
                    if param_value:  # Only update if parameter has a value
                        # Convert age to string without decimal
                        if param_name == 'age':
                            param_value = str(int(float(param_value)))
                        # Handle country normalization
                        elif param_name == 'country' and param_value == 'United States':
                            param_value = 'USA'
                        session['responses'][param_name] = param_value
                        session['collected_params'].add(param_name)
            
            # Check for conversation end intent
            if intent in ['end_conversation', 'goodbye', 'no_interest']:
                await self._handle_conversation_end(lead_id, intent)
                return
            
            # Send the response from Dialogflow
            await self._send_message(lead_id, dialogflow_response['fulfillment_text'])
            
            # Check if all required parameters are collected
            required_params = {'age', 'country', 'interest'}
            if required_params.issubset(session['collected_params']):
                await self._handle_conversation_end(lead_id, 'completed')
                
        except Exception as e:
            logger.error(f"Error processing response for lead {lead_id}: {str(e)}")
            # Send a more specific error message based on the error type
            if "Input text not set" in str(e):
                await self._send_message(lead_id, "I didn't receive your response. Could you please try again?")
            else:
                await self._send_message(lead_id, "I'm sorry, I encountered an error. Please try again.")

    async def _handle_conversation_end(self, lead_id: str, end_type: str):
        """Handle the end of a conversation"""
        try:
            session = self.sessions[lead_id]
            
            # Save the lead data
            self._save_lead_data(lead_id)
            
            # Send final message based on end type
            if end_type == 'no_interest':
                await self._send_message(lead_id, "Thank you for your time. Have a great day!")
            elif end_type == 'completed':
                await self._send_message(lead_id, "Thank you for providing all the information. Our team will contact you soon!")
            else:
                await self._send_message(lead_id, "Thank you for chatting with me. Have a great day!")
            
            # Clean up Dialogflow context
            await self.dialogflow_client.delete_context(lead_id, "initial_greeting")
            
            # Cancel follow-up task
            if lead_id in self.follow_up_tasks:
                logger.info(f"Cancelling follow-up task for lead {lead_id}")
                self.follow_up_tasks[lead_id].cancel()
                del self.follow_up_tasks[lead_id]
            
            # End the session
            if lead_id in self.sessions:
                del self.sessions[lead_id]
                
        except Exception as e:
            logger.error(f"Error handling conversation end for lead {lead_id}: {str(e)}")

    async def _monitor_follow_up(self, lead_id: str):
        """Monitor and handle follow-ups for unresponsive leads"""
        try:
            logger.info(f"Starting follow-up monitoring for lead {lead_id}")
            last_follow_up_time = None
            
            while lead_id in self.sessions:
                session = self.sessions[lead_id]
                current_time = datetime.now()
                
                # Calculate time since last interaction or follow-up
                if last_follow_up_time:
                    time_since_last = current_time - max(session['last_interaction'], last_follow_up_time)
                else:
                    time_since_last = current_time - session['last_interaction']
                
                logger.debug(f"Time since last interaction for lead {lead_id}: {time_since_last.total_seconds()} seconds")
                
                # Send follow-up every 20 seconds of inactivity
                if time_since_last > timedelta(seconds=20):
                    logger.info(f"Sending follow-up to lead {lead_id}")
                    
                    # Get the current question based on missing parameters
                    missing_params = {'age', 'country', 'interest'} - session['collected_params']
                    if missing_params:
                        if 'age' in missing_params:
                            follow_up_msg = "Please provide your age."
                        elif 'country' in missing_params:
                            follow_up_msg = "Please tell me which country you're from."
                        elif 'interest' in missing_params:
                            follow_up_msg = "Please let me know what product or service you're interested in."
                    else:
                        follow_up_msg = "Please complete the form by answering all questions."
                    
                    # Print the follow-up message in the same command prompt
                    print(f"\n{follow_up_msg}")
                    logger.info(f"Follow-up sent to lead {lead_id}: {follow_up_msg}")
                    last_follow_up_time = current_time
                
                await asyncio.sleep(1)  # Check every second
                
        except asyncio.CancelledError:
            logger.info(f"Follow-up monitoring cancelled for lead {lead_id}")
        except Exception as e:
            logger.error(f"Error in follow-up monitoring for lead {lead_id}: {str(e)}")
            if lead_id in self.sessions:
                del self.sessions[lead_id]

    def _save_lead_data(self, lead_id: str):
        """Save lead data to CSV"""
        try:
            session = self.sessions[lead_id]
            
            # Check if any responses were collected
            has_responses = any(session['responses'].values())
            
            new_data = {
                'lead_id': lead_id,
                'name': session['name'],
                'age': session['responses'].get('age', ''),
                'country': session['responses'].get('country', ''),
                'interest': session['responses'].get('interest', ''),
                'status': 'no response' if not has_responses else 'secured'
            }
            
            df = pd.read_csv(self.leads_file)
            if lead_id in df['lead_id'].values:
                df.loc[df['lead_id'] == lead_id] = pd.Series(new_data)
            else:
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_csv(self.leads_file, index=False)
            logger.info(f"Saved data for lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Error saving lead data: {str(e)}")

    def _validate_lead_id(self, lead_id: str) -> bool:
        """Validate if lead_id is unique and properly formatted"""
        try:
            if not lead_id or not isinstance(lead_id, str):
                return False
                
            # Check if lead_id already exists in CSV
            if os.path.exists(self.leads_file):
                df = pd.read_csv(self.leads_file)
                if lead_id in df['lead_id'].values:
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating lead_id: {str(e)}")
            return False

    async def _send_message(self, lead_id: str, message: str):
        """Send message to lead"""
        try:
            print(f"\n{message}")
            logger.info(f"Message sent to lead {lead_id}: {message}")
            return message
        except Exception as e:
            logger.error(f"Error sending message to lead {lead_id}: {str(e)}")
            return None 