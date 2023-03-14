#!/usr/bin/env python3
import argparse
import subprocess
import time
from pathlib import Path

import img2pdf
import selenium
from PIL import Image
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from fucts.roman import roman_sort_with_ints, move_romans_to_front, try_convert_int

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='./VitalSource/')
parser.add_argument('--isbn', required=True)
parser.add_argument('--delay', default=2, type=int, help='Delay between pages to let them load in seconds.')
parser.add_argument('--pages', default=None, type=int, help='Override how many pages to save.')  # TODO
parser.add_argument('--start-page', default=0, type=int, help='Start on this page. Pages start at zero and include any non-numbered pages.')
parser.add_argument('--end-page', default=-1, type=int, help='End on this page.')
parser.add_argument('--chrome-exe', default=None, type=str, help='Path to the Chrome executable. Leave blank to auto-detect.')
parser.add_argument('--disable-web-security', action='store_true', help="If pages aren't loading then you can try disabling CORS protections.")
parser.add_argument('--language', default='eng', help='OCR language. Default: "eng"')
parser.add_argument('--skip-scrape', action='store_true', help="Don't scrape anything, just re-build the PDF from existing files.")
args = parser.parse_args()

args.output = Path(args.output)
args.output.mkdir(exist_ok=True, parents=True)
ebook_output = args.output / f'{args.isbn}.pdf'
ebook_output_ocr = args.output / f'{args.isbn} OCR.pdf'
ebook_files = args.output / args.isbn
ebook_files.mkdir(exist_ok=True, parents=True)

if not args.skip_scrape:
    chrome_options = webdriver.ChromeOptions()
    if args.disable_web_security:
        chrome_options.add_argument('--disable-web-security')
        print('DISABLED WEB SECURITY!')
    chrome_options.add_argument('--disable-http2')  # VitalSource's shit HTTP2 server is really slow and will sometimes send bad data.
    if args.chrome_exe:
        chrome_options.binary_location = args.chrome_exe  # '/usr/bin/google-chrome'
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), chrome_options=chrome_options)

    driver.get(f'https://bookshelf.vitalsource.com')
    input('Press ENTER once logged in...')


    def get_num_pages():
        while True:
            try:
                total = int(driver.execute_script('return document.getElementsByClassName("sc-knKHOI gGldJU")[0].innerHTML').strip().split('/')[-1].strip())
                try:
                    # This element may be empty so just set it to 0
                    current_page = driver.execute_script('return document.getElementsByClassName("InputControl__input-fbzQBk hDtUvs TextField__InputControl-iza-dmV iISUBf")[0].value')
                    if current_page == '' or not current_page:
                        current_page = 0
                except selenium.common.exceptions.JavascriptException:
                    current_page = 0
                return current_page, total
            except selenium.common.exceptions.JavascriptException:
                time.sleep(1)


    def load_book_page(page_id):
        driver.get(f'https://bookshelf.vitalsource.com/reader/books/{args.isbn}/pageid/{page_id}')
        get_num_pages()  # Wait for the page to load
        while len(driver.find_elements(By.CLASS_NAME, "sc-AjmGg dDNaMw")):
            time.sleep(1)


    driver.maximize_window()
    page_num = args.start_page
    load_book_page(page_num)

    _, total_pages = get_num_pages()
    total_pages = 99999999999999999 if args.start_page > 0 else total_pages
    print('Total number of pages:', total_pages)

    page_urls = set()
    failed_pages = set()
    small_pages_redo = set()
    bar = tqdm(total=total_pages)
    bar.update(page_num)
    while page_num < total_pages + 1:
        time.sleep(args.delay)
        retry_delay = 5
        base_url = None
        for page_retry in range(3):  # retry the page max this many times
            largest_size = 0
            for find_img_retry in range(3):
                for request in driver.requests:
                    if request.url.startswith(f'https://jigsaw.vitalsource.com/books/{args.isbn}/images/'):
                        base_url = request.url.split('/')
                        del base_url[-1]
                        base_url = '/'.join(base_url)
                time.sleep(1)
            if base_url:
                break
            bar.write(f'Could not find a matching image for page {page_num}, sleeping {retry_delay}s...')
            time.sleep(retry_delay)
            retry_delay += 5

        page, _ = get_num_pages()
        if not base_url:
            bar.write(f'Failed to get a URL for page {page_num}, retrying later.')
            failed_pages.add(page_num)
        else:
            page_urls.add((page, base_url))
            bar.write(base_url)
            # If this isn't a numbered page we will need to increment the page count
            try:
                int(page)
            except ValueError:
                total_pages += 1
                bar.write(f'Non-number page {page}, increasing page count by 1 to: {total_pages}')
                bar.total = total_pages
                bar.refresh()

        if page_num == args.end_page:
            bar.write(f'Exiting on page {page_num}.')
            break

        # On the first page the back arrow is disabled and will trigger this
        if isinstance(page_num, int) and page_num > 0:
            try:
                if driver.execute_script(f'return document.getElementsByClassName("IconButton__button-bQttMI gHMmeA sc-oXPCX mwNce")[0].disabled'):  # not driver.find_elements(By.CLASS_NAME, 'IconButton__button-bQttMI gHMmeA sc-oXPCX mwNce')[0].is_enabled():
                    bar.write(f'Book completed, exiting.')
                    break
            except selenium.common.exceptions.JavascriptException:
                pass

        # Move to the next page
        del driver.requests
        actions = ActionChains(driver)
        actions.send_keys(Keys.RIGHT)
        actions.perform()
        bar.update()
        page_num += 1
    bar.close()

    print('Re-doing failed pages...')
    bar = tqdm(total=len(failed_pages))
    for page in failed_pages:
        load_book_page(page)
        time.sleep(args.delay)
        retry_delay = 5
        base_url = None
        for page_retry in range(3):  # retry the page max this many times
            largest_size = 0
            for find_img_retry in range(3):
                for request in driver.requests:
                    if request.url.startswith(f'https://jigsaw.vitalsource.com/books/{args.isbn}/images/'):
                        base_url = request.url.split('/')
                        del base_url[-1]
                        base_url = '/'.join(base_url)
                time.sleep(1)
            if base_url:
                break
            bar.write(f'Could not find a matching image for page {page_num}, sleeping {retry_delay}s...')
            time.sleep(retry_delay)
            retry_delay += 5
        page, _ = get_num_pages()
        if not base_url:
            bar.write(f'Failed to get a URL for page {page_num}, retrying later.')
            failed_pages.add(page_num)
        else:
            page_urls.add((page, base_url))
            bar.write(base_url)
            del driver.requests

    time.sleep(1)
    print('All pages scraped! Now downloading images...')

    bar = tqdm(total=len(page_urls))
    for page, base_url in page_urls:
        success = False
        for retry in range(6):
            del driver.requests
            time.sleep(args.delay)
            driver.get(f'{base_url.strip("/")}/2000')  # have to load the page first for cookies reasons
            time.sleep(args.delay)
            retry_delay = 5
            img_data = None
            for page_retry in range(3):  # retry the page max this many times
                largest_size = 0
                for find_img_retry in range(3):
                    for request in driver.requests:
                        if request.url.startswith(f'https://jigsaw.vitalsource.com/books/{args.isbn}/images/'):
                            img_data = request.response.body
                            break
            dl_file = ebook_files / f'{page}.jpg'
            if img_data:
                with open(dl_file, 'wb') as file:
                    file.write(img_data)
                # Re-save the image to make sure it's in the correct format
                img = Image.open(dl_file)
                if img.width != 2000:
                    bar.write(f'Image too small at {img.width}px wide, retrying: {base_url}')
                    driver.get('https://google.com')
                    time.sleep(8)
                    load_book_page(0)
                    time.sleep(8)
                    continue
                img.save(dl_file, format='JPEG', subsampling=0, quality=100)
                del img
                success = True
            if success:
                break
        if not success:
            bar.write(f'Failed to download image: {base_url}')
        bar.update()
    bar.close()
    driver.close()
    del driver
else:
    print('Scrape skipped...')

print('Building PDF...')
page_files = [str(ebook_files / f'{x}.jpg') for x in move_romans_to_front(roman_sort_with_ints([try_convert_int(str(x.stem)) for x in list(ebook_files.iterdir())]))]
pdf = img2pdf.convert(page_files)
with open(ebook_output, 'wb') as f:
    f.write(pdf)

# TODO: maybe scrape book title to name the PDF file?
# TODO: also maybe embed the title in the PDF file?
title = 'test title'

print('Running OCR...')
subprocess.run(f'ocrmypdf -l {args.language} --title "{title}" --jobs $(nproc) --output-type pdfa "{ebook_output}" "{ebook_output_ocr}"', shell=True)

# TODO: scrape table of contents and insert


# TODO: fix blank pages causing duplicaged pages
