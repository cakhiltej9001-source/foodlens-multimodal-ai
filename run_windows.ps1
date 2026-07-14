if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}
# Calling python.exe directly avoids PowerShell execution-policy problems.
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m streamlit run app.py
