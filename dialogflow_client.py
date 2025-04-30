from google.cloud import dialogflow
import os
import logging
import json
import socket
import requests

logger = logging.getLogger(__name__)

class DialogflowClient:
    def __init__(self):
        try:
            # Verify network connectivity
            socket.create_connection(("dialogflow.googleapis.com", 443), timeout=5)
            
            # Verify credentials
            if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
            
            if not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
                raise FileNotFoundError(f"Credentials file not found at {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
            
            # Initialize clients
            self.session_client = dialogflow.SessionsClient()
            self.contexts_client = dialogflow.ContextsClient()
            
            # Verify project ID
            self.project_id = os.getenv('PROJECT_ID')
            if not self.project_id:
                raise ValueError("PROJECT_ID environment variable is not set")
                
            logger.info("Dialogflow client initialized successfully")
            
        except socket.gaierror as e:
            logger.error(f"Network error: Could not resolve dialogflow.googleapis.com. Please check your internet connection and DNS settings.")
            raise
        except Exception as e:
            logger.error(f"Error initializing Dialogflow client: {str(e)}")
            raise
    
    def _session_path(self, session_id: str):
        return self.session_client.session_path(self.project_id, session_id)

    def _context_path(self, session_id: str, context_name: str):
        return self.contexts_client.context_path(self.project_id, session_id, context_name)

    async def detect_intent(self, session_id: str, text: str, language_code: str = "en"):
        """
        Detect intent from text using Dialogflow ES
        Returns a dictionary containing intent and response information
        """
        try:
            session = self._session_path(session_id)
            text_input = dialogflow.TextInput(text=text, language_code=language_code)
            query_input = dialogflow.QueryInput(text=text_input)

            response = self.session_client.detect_intent(
                request={"session": session, "query_input": query_input}
            )

            # Extract information directly from the response object
            query_result = response.query_result
            
            # Get intent name
            intent_name = None
            if query_result and query_result.intent:
                intent_name = query_result.intent.display_name
            
            # Get confidence
            confidence = 0.0
            if query_result:
                confidence = query_result.intent_detection_confidence
            
            # Get fulfillment text
            fulfillment_text = ""
            if query_result:
                fulfillment_text = query_result.fulfillment_text
            
            # Get parameters
            parameters = {}
            if query_result and query_result.parameters:
                # Convert parameters to a simple dictionary
                parameters = {}
                for key, value in query_result.parameters.items():
                    if hasattr(value, 'string_value'):
                        parameters[key] = value.string_value
                    else:
                        parameters[key] = str(value)
            
            # Check if all required parameters are present
            all_required_params_present = False
            if query_result:
                all_required_params_present = query_result.all_required_params_present
            
            # Get action
            action = ""
            if query_result:
                action = query_result.action
            
            return {
                "intent": intent_name,
                "confidence": confidence,
                "fulfillment_text": fulfillment_text,
                "parameters": parameters,
                "all_required_params_present": all_required_params_present,
                "action": action,
                "raw_response": None
            }
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}")
            return {
                "intent": None,
                "confidence": 0,
                "fulfillment_text": "I'm sorry, I encountered an error. Please try again.",
                "parameters": {},
                "all_required_params_present": False,
                "action": "",
                "raw_response": None
            }

    async def create_context(self, session_id: str, context_name: str, lifespan_count: int = 5):
        """Create a new context for the session"""
        try:
            parent = self._session_path(session_id)
            context = {
                "name": self._context_path(session_id, context_name),
                "lifespan_count": lifespan_count
            }
            self.contexts_client.create_context(parent=parent, context=context)
            return True
        except Exception as e:
            logger.error(f"Error creating context: {str(e)}")
            return False

    async def delete_context(self, session_id: str, context_name: str):
        """Delete a context from the session"""
        try:
            context_path = self._context_path(session_id, context_name)
            self.contexts_client.delete_context(name=context_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting context: {str(e)}")
            return False
