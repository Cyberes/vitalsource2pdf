# vitalsource2pdf

_Ultra-high quality PDFs from VitalSource._

**I have graduated and am no longer able to maintain this project. Feel free to fork and build upon my work.**

**<https://github.com/Cyberes/vitalsource2pdf/network>**

This is an automated, all-in-one scraper to convert VitalSource textbooks into PDFs with no compromises. Features include:

- Automated download of pages.

- Automated OCR.

- Correct page numbering (including Roman numerals at the beginning).

- Table of contents creation.

- No funny stuff. No weird endpoints and no hacky scraping.

**[OFFICIALLY HATED BY VITALSOURCE](https://github.com/Cyberes/vitalsource2pdf/issues/1)**
  

This scraper is almost completely transparent and all actions are ones that a normal user would do. This allows us to defeat all of [VitalSource's anti-scraping protections](https://get.vitalsource.com/hubfs/Content/INTL/Digital%20Discovery%20Day/Resource%20Page/Resources/Content%20Security%20Position%20Paper.pdf).



The goal of this project is for it to "just work." There are many other VitalSource scrapers out there that are weird, poorly designed, or broken. I designed my scraper to be simple while producing the highest-quality PDF possible.



**This only works with PDF books!** The URL must look something like this: `https://bookshelf.vitalsource.com/reader/books/{isbn}/pageid/{page_id}`

**This URL format won't work!** `https://bookshelf.vitalsource.com/reader/books/{isbn}/epubcfi/6/22[%3Bvnd.vst.idref%3Dt{author}{isbn}c00_02]!/4`

Maybe someday the scraper could be updated to work with more book formats...



## Install

This program only works on Linux. You can use WSL on Windows.

```bash
sudo apt install ocrmypdf jbig2dec
pip install -r requirements.txt
```

Make sure you have Chrome installed. If you have both Chrome and Chrominium you can use `--chrome-exe` to specify the path to `google-chrome`.

The Webdriver binary will be automatically downloaded.



## Use

```bash
./vitalsource2pdf.py --isbn [your book's ISBN number]
```

A browser window will pop up so you can log into VitalSource. Press the `ENTER` key when you are ready.

You can use `--output` to control where the files are created. By default it creates a folder named `VitalSource`.

If your network is slow, use `--delay` to allow more time for the files to download.

Make sure to leave the window maximized as the content scaling will mess with the scraper.

You may want to run the scraper two or three times to make sure you have downloaded all the pages. It should work the first time, but you never know.



### What This Scraper Doesn't Do

Guide you through step-by-step. You are expected to have the required technical knowledge and understand what is happening behind the scenes in order to troubleshoot any issues.

You will also have to double check the output PDF to make sure everything is as it should be.



### How it Works

This scraper uses Selenium to load the ebook viewer webpage. It then navigates through the book page by page and records network requests. After each page it will analyze the requests and find one matching the format of the page image. It then saves that request for later. Once the scraper has read the entire book it will go back through and load the highest-quality images in the browser and save them.
