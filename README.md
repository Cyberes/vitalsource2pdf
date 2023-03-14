# vitalsource2pdf

_Ultra-high quality PDFs from VitalSource._

This is an automated, all-in-one scraper to convert VitalSource textbooks into PDFs. Features include:

- Automated download of pages.
- Automated OCR.
- Correct page numbers (including Roman numerals at the beginning). There might be some issues with wierd page numbers at the end
  of the book.
- Table of contents creation.
- No funny stuff. No wierd endpoints are used and no hacky scraping is preformed.
- Almost completly transparent. All actions are ones that a normal user would do.

The goal of this project is for this to "just work." There are many other VitalSource scrapers out there that are wierd, poorly
designed, or are broken. I designed my scraper to be as simple while producing the highest-quality PDF possible.

## Install

```bash
pip install -r requirements.txt
```

Make sure you have Chrome installed as it uses Selenium. The Webdriver binary will be automatically downloaded.

## Use

```bash
./vitalsource2pdf.py --isbn [your book's ISBN number]
```

A browser window will pop up so you can log into VitalSource. Press the `ENTER` key when you are ready.

You can use `--output` to control where the files are created. By default it creates a folder named `VitalSource`.

If your network is slow, use `--delay` to allow more time for the files to download.

### What This Scraper Doesn't Do

Guide you through step-by-step. You are expected to have the required technical knowledge and understand what
is happening behind the scenes in order to troubleshoot any issues.

You will also have to double check the output PDF to make sure everything is as it should be.

### How it Works

This scraper uses Selenium to load the ebook viewer webpage. It then navigates through the book page by page and records network
requests. After each page it will analyze the requests and find one matching the format of the page image. It then saves
that request to a `.jpg`.

Once all images are downloaded, a PDF is created.

Then `pytesseract` is used to add text to the page images.

Finally, the table of contents is scraped and added to the PDF. 