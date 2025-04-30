import asyncio
import random
import logging
from datetime import datetime
from sales_agent import SalesAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LeadSimulator:
    def __init__(self):
        self.agent = SalesAgent()
        self.names = ["John", "Sarah", "Michael", "Emily", "David", "Lisa"]
        self.countries = ["USA", "UK", "Canada", "Australia", "India", "Germany"]
        self.interests = ["Product A", "Product B", "Service X", "Service Y"]

    def generate_lead_id(self):
        """Generate a unique lead ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_num = random.randint(10000, 99999)
        return f"word_{timestamp}_{random_num}"

    async def simulate_lead(self, name=None, delay_responses=False):
        """Simulate a lead interaction"""
        lead_id = self.generate_lead_id()
        name = name or random.choice(self.names)
        
        logger.info(f"Starting simulation for lead {lead_id} ({name})")
        
        # Start the lead session
        await self.agent.handle_lead(lead_id, name, "simulation")
        
        # Simulate responses
        responses = [
            "Yes, that's fine",  # Initial response
            str(random.randint(18, 65)),  # Age
            random.choice(self.countries),  # Country
            random.choice(self.interests)  # Interest
        ]
        
        for response in responses:
            if delay_responses:
                # Random delay between 5-15 seconds
                delay = random.randint(5, 15)
                logger.info(f"Waiting {delay} seconds before next response")
                await asyncio.sleep(delay)
            
            logger.info(f"Sending response: {response}")
            await self.agent.process_response(lead_id, response)
            
            # Small delay between responses
            await asyncio.sleep(1)
        
        logger.info(f"Simulation completed for lead {lead_id}")

    async def simulate_multiple_leads(self, count=3, delay_responses=False):
        """Simulate multiple lead interactions"""
        tasks = []
        for _ in range(count):
            task = asyncio.create_task(self.simulate_lead(delay_responses=delay_responses))
            tasks.append(task)
            # Small delay between starting leads
            await asyncio.sleep(2)
        
        await asyncio.gather(*tasks)

    async def simulate_follow_up_test(self):
        """Simulate a lead interaction to test follow-ups"""
        lead_id = self.generate_lead_id()
        name = random.choice(self.names)
        
        logger.info(f"Starting follow-up test for lead {lead_id} ({name})")
        
        # Start the lead session
        await self.agent.handle_lead(lead_id, name, "follow_up_test")
        
        # Send initial response
        await self.agent.process_response(lead_id, "Yes, that's fine")
        
        # Wait for follow-ups (should trigger after 20 and 40 seconds)
        logger.info("Waiting for follow-ups...")
        await asyncio.sleep(60)  # Wait for 60 seconds to see both follow-ups
        
        # Send final response
        await self.agent.process_response(lead_id, "I'm interested in Product A")
        
        logger.info("Follow-up test completed")

async def main():
    simulator = LeadSimulator()
    
    print("Choose simulation type:")
    print("1. Single lead simulation")
    print("2. Multiple leads simulation")
    print("3. Follow-up test")
    print("4. Delayed responses test")
    
    choice = input("Enter your choice (1-4): ")
    
    try:
        if choice == "1":
            name = input("Enter lead name (or press Enter for random): ")
            await simulator.simulate_lead(name if name else None)
        elif choice == "2":
            count = int(input("Enter number of leads to simulate: "))
            await simulator.simulate_multiple_leads(count)
        elif choice == "3":
            await simulator.simulate_follow_up_test()
        elif choice == "4":
            count = int(input("Enter number of leads to simulate: "))
            await simulator.simulate_multiple_leads(count, delay_responses=True)
        else:
            print("Invalid choice")
    except Exception as e:
        logger.error(f"Error during simulation: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 