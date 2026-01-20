Installing wkhtmltopdf (Windows)

1) Download and install:
   - Go to https://wkhtmltopdf.org/downloads.html and download the Windows (msvc) installer.
   - Run the installer and install to the default location (usually `C:\Program Files\wkhtmltopdf`).

2) Make sure the binary is available:
   - Either add the `bin` folder to your PATH, e.g. `C:\Program Files\wkhtmltopdf\bin`.
   - OR set an environment variable `WKHTMLTOPDF_PATH` pointing to the executable, e.g.
     - In PowerShell (temporary for session):
       $env:WKHTMLTOPDF_PATH = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
     - To set it permanently, update System Environment Variables in Windows Settings.

3) Verify installation:
   - Open a new terminal and run `wkhtmltopdf --version` (or run `Get-Command wkhtmltopdf` in PowerShell).
   - If this prints a version, you are good to go.

4) Install Python dependencies:
   - From the project root run:
     pip install -r requirements.txt

Notes:
- The app uses `pdfkit` and will try to use `WKHTMLTOPDF_PATH` if present; otherwise it relies on `wkhtmltopdf` being on PATH.
- If PDF generation fails, the app now flashes a helpful error message on the reports page explaining the underlying error.

If you prefer not to install wkhtmltopdf, alternatives include tools like WeasyPrint or headless Chromium (puppeteer/pyppeteer), but they require code changes to the project.