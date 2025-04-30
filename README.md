# Sales Agent with Dialogflow Integration

A Python-based sales agent that uses Dialogflow for natural language processing and lead management. The agent handles lead interactions, collects information, and manages follow-ups automatically.

## Features

- Natural language processing using Dialogflow
- Automated lead information collection
- Smart follow-up system
- Lead data management and storage
- Error handling and logging
- Asynchronous operation

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Cloud account with Dialogflow API enabled
- Dialogflow ES agent created and configured

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sales-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with:
```
PROJECT_ID=your-dialogflow-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

5. Configure Dialogflow:
- Create a Dialogflow ES agent
- Set up the following intents:
  - `initial_greeting`
  - `collect_age`
  - `collect_country`
  - `collect_interest`
  - `follow_up_message`
  - `second_follow_up`
  - `end_conversation`

## Usage Guide

### Running the Agent

1. Start the agent:
```bash
python sales_agent.py
```

2. Simulate a lead interaction:
```bash
python simulate_lead.py
```
3. Test the agent on opening of word file which is set as a trigger
```bash
python word_monitor.py

### Monitoring

- Check the `sales_agent.log` file for detailed logs
- View lead data in `leads.csv`

## Design Decisions

### Architecture

1. **Asynchronous Design**
   - Uses `asyncio` for non-blocking operations
   - Enables concurrent handling of multiple leads
   - Efficient follow-up monitoring

2. **Dialogflow Integration**
   - Uses Dialogflow ES for natural language processing
   - Maintains conversation context
   - Handles intent detection and parameter extraction

3. **Lead Management**
   - Stores lead data in CSV format
   - Tracks conversation state
   - Manages follow-up timing

4. **Error Handling**
   - Comprehensive error logging
   - Graceful error recovery
   - User-friendly error messages

### Assumptions

1. **Lead Information**
   - Required fields: name, age, country, interest
   - Optional fields: source, status

2. **Follow-up Timing**
   - First follow-up after 20 seconds of inactivity
   - Second follow-up after 40 seconds of inactivity

3. **Conversation Flow**
   - Linear progression through information collection
   - Ability to handle interruptions and resume
   - Support for early termination

## Testing

### Test Cases

1. **Basic Conversation Flow**
   - Complete information collection
   - Proper parameter extraction
   - Correct intent detection

2. **Error Handling**
   - Empty responses
   - Invalid inputs
   - Network errors

3. **Follow-up System**
   - Timing accuracy
   - Response handling
   - Task cancellation

4. **Data Management**
   - Lead data storage
   - Session management
   - CSV file operations

### Simulation Tools

1. **Lead Simulator**
   - Simulates lead form submissions
   - Tests response handling
   - Verifies follow-up timing

2. **Delay Simulator**
   - Tests follow-up timing
   - Verifies inactivity handling
   - Tests session cleanup

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

