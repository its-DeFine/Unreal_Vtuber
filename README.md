# Livepeer VTuber External Capability (BYOC)

This repository hosts the official VTuber external capability integration for Livepeer, utilizing a Bring Your Own Compute (BYOC) model. It enables users to integrate advanced VTubing functionalities with the Livepeer network.

## 📢 Early Release Note

Please be aware that this is an early release. We are actively working on simplifying the installation and setup process. We appreciate your understanding and feedback!

##  Prerequisites

Before you begin, ensure you have the following installed:
*   Git
*   Node.js and npm (Node Package Manager)
*   Minimum 20GB of RAM
*   Python 3.10
*   Docker Desktop
*   Unreal Engine Metahuman with LiveLink enabled
*   A topped-up Livepeer Gateway account (you can top up any account at [gwid.io](https://gwid.io/))

## 🚀 Getting Started

Follow these steps to set up the VTuber external capability:

### 1. Clone Repositories

You'll need to clone two main repositories. Open your terminal and run the following commands:

```bash
# Clone the NeuroSync-Core repository (BYOC branch)
git clone -b BYOC https://github.com/its-DeFine/NeuroSync-Core.git

# Clone the Eliza Livepeer Integration repository (scb-org branch)
git clone -b scb-org https://github.com/its-DeFine/eliza-livepeer-integration.git
```

This will download the necessary codebases into your local environment. We recommend cloning them into a common parent directory for organizational purposes, for example, a directory named `livepeer-vtuber-byoc/`.

### 2. Configure Environment Variables

An example environment file is provided in the project root as `.example.env`.

*   Copy this file to `.env` and populate the values as needed. This single file covers both the NeuroSync and Eliza configuration options.
    *   Note: Eliza-specific variables can be left blank if you are not using those features.
    *   For orchestrator-relevant variables, please refer to the information available at [https://github.com/ad-astra-video/livepeer-app-pipelines](https://github.com/ad-astra-video/livepeer-app-pipelines).
*   Carefully fill in the required values in your newly created `.env` file.

```bash
# Example:
cp .example.env .env
# Edit the file to add your values
nano .env  # Or use your preferred editor
```

### 3. Build the Web Application

The user interface for managing and interacting with the VTuber capabilities is provided as a web application.

*   Navigate to the `webapp/` directory in this repository:
    ```bash
    cd webapp
    ```

*   Install the necessary dependencies:
    ```bash
    npm install
    ```

*   Build the application:
    ```bash
    npm run build
    ```

### 4. Running the System

Once your repositories are cloned and environment variables are configured, follow these steps:

1.  **Launch the Docker Containers**:
    Open your terminal in the directory where you cloned the repositories (e.g., inside `livepeer-vtuber-byoc/` if you followed the recommendation, ensuring `docker-compose.bridge.yml` and `docker-compose.byoc.yml` are accessible or correctly pathed) and run the following command. This command will build the necessary Docker images and then start the services. The build process can take some time, and logs will be saved to `build_logs.txt`.
    ```bash
    docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml build --progress=plain > build_logs.txt 2>&1 && docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml up
    ```

2.  **Access the User Interface**:
    Once the containers are up and running, you can access the web UI by navigating to `http://localhost:8088` in your web browser.

3.  **Submit Transactions**:
    Follow the instructions in the UI to submit the necessary transactions from your wallet to interact with the Livepeer network.

4.  **Send Prompts to Your Metahuman**:
    After the job is successfully initiated and running, you can send prompts to your Metahuman. For example, you can change the text value in the following `curl` POST request to send a new prompt:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"text":"Hello from curl"}' http://localhost:5001/process_text
    ```

Enjoy your VTubing experience!

## 🛠️ Simplifying Installation

We are actively working on streamlining this setup process. Future updates will aim to provide a more straightforward installation experience, potentially through unified scripts or enhanced Docker configurations.

## 🤝 Contributing

Contributions are welcome! If you encounter any issues, have suggestions for improvements, or would like to contribute to the development, please feel free to open an issue or submit a pull request on the respective GitHub repositories.

## 📄 License

This project and its components are distributed under their respective licenses. Please refer to the `LICENSE` files within each cloned repository for detailed information.
*   [NeuroSync-Core License](https://github.com/its-DeFine/NeuroSync-Core/blob/BYOC/LICENCE)
*   [eliza-livepeer-integration License](https://github.com/its-DeFine/eliza-livepeer-integration/blob/scb-org/LICENSE)

---

We are excited to see what you build with this Livepeer VTuber integration! 