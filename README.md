
## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.x (It's recommended to use Python 3.9 or higher for best compatibility)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-project-directory>
    ```
2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    ```
3.  **Activate the virtual environment:**
    * On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    * On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
4.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    
5. **.env Configuration for Vertex AI
Create a file named .env in the root directory of your project and add the following lines:**
    ```bash
    # If using Google Cloud services (including Vertex AI), set the following environment variables..
    GOOGLE_GENAI_USE_VERTEXAI=TRUE
    GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id  # Replace with your actual Google Cloud Project ID
    GOOGLE_CLOUD_LOCATION=asia-south1                 # Replace with your desired Vertex AI region (e.g., us-central1, europe-west1).
    ```

### Running the Application

Once you've installed the dependencies, you can run the main application:

```bash
python main.py
