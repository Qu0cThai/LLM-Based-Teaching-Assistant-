# AI Teaching Assistant

## 1. Development Environment

To ensure the system runs smoothly, your machine should meet the
following requirements.

### Hardware Requirements

  -----------------------------------------------------------------------
  Component                           Requirement
  ----------------------------------- -----------------------------------
  CPU                                 Multi-core processor (e.g., Intel
                                      Core i5/i7 10th Gen or AMD Ryzen
                                      5/7)

  RAM                                 Minimum 16 GB

  GPU                                 Optional but highly recommended:
                                      NVIDIA GPU with at least 6 GB VRAM
                                      (e.g., RTX 3060 or higher)

  Storage                             At least 10 GB of free SSD space
                                      for the application, Python
                                      environments, and local models
  -----------------------------------------------------------------------

### Software Requirements

-   **Python:** 3.9 or higher
-   **Database:** MySQL Server (running locally)
-   **LLM engine:** [Ollama](https://ollama.com/) for downloading and
    running local language models

### Key Python Libraries

-   Streamlit
-   PyMuPDF (`fitz`)
-   `python-docx`
-   `mysql-connector-python`
-   NumPy

------------------------------------------------------------------------

## 2. Installation

### Step 1: Set Up the Database

1.  Make sure MySQL Server is installed and running locally.
2.  Create a database named `teaching_assistant`.

``` sql
CREATE DATABASE teaching_assistant;
```

The application connects to MySQL on `localhost` using the username
`root` and a password. If necessary, update the database credentials in
the `get_db_connection()` function in `io_utils.py`.

### Step 2: Download Ollama Models

The system uses locally hosted models to help keep document data
private.

Install [Ollama](https://ollama.com/) if you have not already, then run:

``` bash
ollama pull qwen2.5-coder:3b
ollama pull mxbai-embed-large
```

### Step 3: Install Python Dependencies

It is recommended to create and activate a Python virtual environment
before installing the dependencies.

Install the required packages with:

``` bash
pip install streamlit streamlit-authenticator mysql-connector-python PyMuPDF python-docx ollama numpy
```

------------------------------------------------------------------------

## 3. Running the Application

1.  Open a terminal or command prompt in the project root directory (the
    directory containing `app.py`).
2.  Start the Streamlit application:

``` bash
streamlit run app.py
```

3.  Your default web browser should open the application automatically.
    If it does not, navigate to:

``` text
http://localhost:8501
```

### Account Registration

-   On the login screen, select **Register here** to create an account.
-   The first user to register is automatically granted administrator
    privileges.

------------------------------------------------------------------------

## 4. Troubleshooting Notes

-   **Stuck on the login page after deleting a user:** If you delete a
    user without logging out and become stuck on the login page, clear
    the page cache. The application should then work normally.
-   **Unable to delete questions, tests, or lesson plans:** Reload the
    page and try again.

------------------------------------------------------------------------

## 5. Changing the Language Model

You can make the system use a larger language model without rewriting
the application code.

1.  Open a terminal and download the model you want. For example:

    ``` bash
    ollama pull llama3
    ```

2.  Open `config.py`.

3.  Update the model variables to the name of the model you downloaded:

    ``` python
    MODEL_FAST = "your-new-model-name"
    MODEL_PLANNER = "your-new-model-name"
    ```

4.  Restart the Streamlit application.
