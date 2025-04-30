import psutil
import asyncio
from datetime import datetime
import logging
from sales_agent import SalesAgent
import time
import os
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('word_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WordMonitor:
    def __init__(self):
        self.agent = SalesAgent()
        self.active_leads = set()  # Track active lead IDs
        self.active_pids = set()   # Track PIDs with active conversations
        self.process_name = "WINWORD.EXE"
        self.terminal_width = 80  # Default terminal width
        self.processed_pids = set()  # Track processed Word PIDs
        self.last_detection_time = {}  # Track last detection time per PID
        self.cooldown_seconds = 120  # 2 minutes cooldown for follow-ups
        
        try:
            self.terminal_width = os.get_terminal_size().columns
        except:
            pass

    def is_word_running(self):
        """Check for new Word processes that haven't been processed yet"""
        current_pids = set()
        new_pids = set()
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == self.process_name.lower():
                    pid = proc.info['pid']
                    current_pids.add(pid)
                    
                    # Only consider new PIDs that don't have active conversations
                    if (pid not in self.active_pids and 
                        pid not in self.processed_pids):
                        new_pids.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Clean up old PIDs
        self.processed_pids = self.processed_pids.intersection(current_pids)
        self.active_pids = self.active_pids.intersection(current_pids)
        
        return new_pids

    def _print_separator(self, lead_id: str):
        """Print a separator line with lead ID"""
        separator = f"=== Conversation for Lead ID: {lead_id} ==="
        print("\n" + "=" * self.terminal_width)
        print(separator.center(self.terminal_width))
        print("=" * self.terminal_width + "\n")

    async def handle_new_lead(self, pid: int):
        """Handle a new lead in a separate process"""
        try:
            # Generate unique lead ID with PID
            lead_id = f"word_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pid}"
            
            if lead_id in self.active_leads:
                logger.warning(f"Lead {lead_id} already active")
                return
                
            self.active_leads.add(lead_id)
            self.active_pids.add(pid)
            self.processed_pids.add(pid)
            self.last_detection_time[pid] = datetime.now()
            
            logger.info(f"Starting new conversation for Word PID {pid} (Lead ID: {lead_id})")
            
            # Start a new Python process for this lead
            script_path = os.path.abspath(__file__)
            subprocess.Popen([
                sys.executable,
                script_path,
                '--lead',
                lead_id,
                str(pid)  # Pass PID to the conversation process
            ], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
        except Exception as e:
            logger.error(f"Error starting new process for PID {pid}: {str(e)}")

    async def handle_lead_conversation(self, lead_id: str, pid: int):
        """Handle the actual conversation for a lead"""
        try:
            # Clear screen and show new conversation
            os.system('cls' if os.name == 'nt' else 'clear')
            self._print_separator(lead_id)
            
            # Get lead information from terminal
            print(f"New lead detected! Lead ID: {lead_id}")
            name = input("Please enter your name: ")
            
            # Start conversation with agent
            await self.agent.handle_lead(lead_id, name, source="word_trigger")
            
            # Process responses
            while True:
                try:
                    # Get user input
                    response = input("\nYour response: ")
                    
                    if response.lower() == 'exit':
                        break
                    
                    # Process the response
                    await self.agent.process_response(lead_id, response)
                    
                    # Check if the session is still active
                    if lead_id not in self.agent.sessions:
                        # Wait a moment to ensure all messages are displayed
                        await asyncio.sleep(2)
                        print("\nPress Enter to close this window...")
                        input()  # Wait for user to press Enter
                        break
                    
                except Exception as e:
                    logger.error(f"Error in conversation: {str(e)}")
                    break
                
        except Exception as e:
            logger.error(f"Error handling lead {lead_id}: {str(e)}")
        finally:
            # Clean up the follow-up task if it exists
            if lead_id in self.agent.sessions and self.agent.sessions[lead_id]['follow_up_task']:
                self.agent.sessions[lead_id]['follow_up_task'].cancel()
            
            print(f"\nConversation ended for Lead ID: {lead_id}")
            print("=" * self.terminal_width)
            self.active_leads.remove(lead_id)
            self.active_pids.remove(pid)
            
            # Wait for user to see the final message and press Enter
            print("\nPress Enter to close this window...")
            input()

    async def monitor(self):
        logger.info("Starting Word monitor...")
        print("\nWord Monitor Started")
        print("The agent will activate when Microsoft Word is opened")
        print("Press Ctrl+C to stop the monitor\n")
        
        while True:
            new_pids = self.is_word_running()
            for pid in new_pids:
                await self.handle_new_lead(pid)
            await asyncio.sleep(1)

async def main():
    # Check if this is a lead conversation process
    if len(sys.argv) > 1 and sys.argv[1] == '--lead':
        lead_id = sys.argv[2]
        pid = int(sys.argv[3])
        monitor = WordMonitor()
        await monitor.handle_lead_conversation(lead_id, pid)
    else:
        # This is the main monitor process
        monitor = WordMonitor()
        await monitor.monitor()

if __name__ == "__main__":
    asyncio.run(main())