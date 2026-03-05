from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from services.csv_ingest_service import ingest_csv

router = APIRouter()


@router.get("/upload", response_class=HTMLResponse)
def upload_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload CSV</title>
        <style>
            :root {
                --bg-main: #2F2F2F;
                --bg-card: #3A3A3A;
                --bg-card-hover: #444444;
                --border-default: #505050;
                --text-primary: #F2F2F2;
                --text-secondary: #C8C8C8;
                --text-muted: #9A9A9A;
                --color-income: #3FB950;
                --color-expense: #F85149;
                --color-budget: #58A6FF;
                --color-warning: #F2CC60;
            }

            body {
                font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                padding: 32px;
                background: var(--bg-main);
                color: var(--text-primary);
                margin: 0;
            }

            h1 {
                font-size: 28px;
                margin: 0 0 32px 0;
                color: var(--text-primary);
            }

            h2 {
                font-size: 16px;
                margin: 24px 0 16px 0;
                color: var(--text-primary);
                font-weight: 600;
            }

            .card {
                background: var(--bg-card);
                border: 1px solid var(--border-default);
                border-radius: 8px;
                padding: 16px;
                max-width: 500px;
                margin-bottom: 24px;
            }

            label {
                display: block;
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            input[type="file"] {
                display: block;
                width: 100%;
                padding: 12px;
                background: var(--bg-main);
                border: 2px dashed var(--border-default);
                border-radius: 6px;
                color: var(--text-primary);
                margin-bottom: 16px;
                cursor: pointer;
                font-size: 14px;
            }

            input[type="file"]:hover {
                border-color: var(--color-budget);
                background: rgba(88, 166, 255, 0.05);
            }

            button {
                padding: 8px 14px;
                cursor: pointer;
                background: var(--color-budget);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                transition: background 0.2s;
                width: 100%;
            }

            button:hover {
                background: #6CB6FF;
            }

            button:disabled {
                background: var(--text-muted);
                cursor: not-allowed;
            }

            p {
                color: var(--text-primary);
                line-height: 1.5;
                margin: 8px 0;
            }

            .success {
                background: rgba(63, 185, 80, 0.1);
                border: 1px solid var(--color-income);
                color: var(--color-income);
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 16px;
                font-size: 14px;
            }

            .error {
                background: rgba(248, 81, 73, 0.1);
                border: 1px solid var(--color-expense);
                color: var(--color-expense);
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 16px;
                font-size: 14px;
            }

            .info {
                color: var(--text-muted);
                font-size: 12px;
                margin-top: 12px;
                line-height: 1.6;
            }

            a {
                color: var(--color-budget);
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <h1>Upload CSV</h1>
        <a href="/dashboard">← Back to Dashboard</a>

        <div class="card">
            <h2>Upload Transaction File</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <label for="csvFile">Select CSV File</label>
                <input type="file" id="csvFile" name="file" accept=".csv" required>
                
                <div id="statusMessage"></div>
                
                <button type="submit" id="submitBtn">Upload</button>

                <div class="info">
                    <strong>Expected CSV Format:</strong><br>
                    Date, Description, Amount, Category<br>
                    <em>Ensure dates are in YYYY-MM-DD format.</em>
                </div>
            </form>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const fileInput = document.getElementById('csvFile');
                const statusMessage = document.getElementById('statusMessage');
                const submitBtn = document.getElementById('submitBtn');
                
                if (!fileInput.files.length) {
                    statusMessage.innerHTML = '<div class="error">Please select a file.</div>';
                    return;
                }

                const file = fileInput.files[0];
                const formData = new FormData();
                formData.append('file', file);

                submitBtn.disabled = true;
                submitBtn.textContent = 'Uploading...';

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.success) {
                        statusMessage.innerHTML = '<div class="success">' + 
                            'CSV uploaded successfully! Processed ' + (result.rows_processed || 'unknown') + ' rows.' +
                            '</div>';
                        fileInput.value = '';
                    } else {
                        statusMessage.innerHTML = '<div class="error">' + 
                            (result.error || 'Failed to upload CSV.') +
                            '</div>';
                    }
                } catch (error) {
                    statusMessage.innerHTML = '<div class="error">Error uploading file: ' + error.message + '</div>';
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Upload';
                }
            });
        </script>
    </body>
    </html>
    """


@router.post("/upload")
def upload_csv(file: UploadFile = File(...)):
    contents_bytes = file.file.read()

    try:
        contents = contents_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"success": False, "error": "File must be UTF-8 encoded CSV"}

    return ingest_csv(contents)