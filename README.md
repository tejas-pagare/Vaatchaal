# Travel Companion AI

Travel Companion AI is a multi-agent application that builds tailored travel itineraries. It features a rich, interactive Streamlit frontend and leverages LangGraph to orchestrate a team of specialized AI agents.

## Features

* **Multi-Agent Intelligence**: A supervisor agent orchestrates various specialists including:
  * Flight Specialist (via Aviationstack MCP)
  * Accommodation Specialist (via Tavily MCP)
  * Weather Specialist (via OpenWeather MCP)
  * Budget Analyst
  * Itinerary Builder
* **Interactive UI**: Clean, modern interface built with Streamlit, featuring an interactive agent execution trace.
* **Visual Itinerary**: Photo-based day-by-day timelines and interactive route mapping.
* **Export Options**: Download generated schedules as PDF files.
* **Human-in-the-Loop**: Interactive approval flow allowing users to provide feedback and refine the generated itinerary before finalization.
* **Benchmarking Suite**: Includes an evaluation framework for testing agent performance on various scenarios (argument correctness, failure recovery, tool confusion, etc.).

## Project Structure

* `frontend.py`: Streamlit application entry point.
* `main.py`: Core application logic and execution scripts.
* `graph/`: LangGraph definitions and agent routing logic.
* `agents/`: Individual agent implementations.
* `mcp_tools/`: Integrations with Model Context Protocol servers.
* `utils/`: Helper services for mapping, PDF generation, and UI icons.
* `benchmark/`: Evaluation datasets and metrics runner.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tejas-pagare/Vaatchaal.git
   cd vaat
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory and add your required API keys (e.g., Groq API Key, OpenWeather API Key).
   ```bash
   GROQ_API_KEY=your_groq_api_key
   OPENWEATHER_API_KEY=your_openweather_api_key
   ```

## Usage

Start the interactive web application using Streamlit:

```bash
streamlit run frontend.py
```

## Contributing

Contributions are welcome. Please open an issue or submit a pull request with your improvements.
