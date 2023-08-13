#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import img2pdf
import selenium
from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from pagelabels import PageLabelScheme, PageLabels
from pdfrw import PdfReader as pdfrw_reader
from pdfrw import PdfWriter as pdfrw_writer
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from fucts.roman import move_romans_to_front, roman_sort_with_ints, try_convert_int

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='./output/')
parser.add_argument('--yuzu', default=False)
parser.add_argument('--isbn', required=True)
parser.add_argument('--delay', default=2, type=int, help='Delay between pages to let them load in seconds.')
parser.add_argument('--pages', default=None, type=int, help='Override how many pages to save.')  # TODO
parser.add_argument('--start-page', default=0, type=int, help='Start on this page. Pages start at zero and include any non-numbered pages.')
parser.add_argument('--end-page', default=-1, type=int, help='End on this page.')
parser.add_argument('--chrome-exe', default=None, type=str, help='Path to the Chrome executable. Leave blank to auto-detect.')
parser.add_argument('--disable-web-security', action='store_true', help="If pages aren't loading then you can try disabling CORS protections.")
parser.add_argument('--language', default='eng', help='OCR language. Default: "eng"')
parser.add_argument('--skip-scrape', action='store_true', help="Don't scrape anything, just re-build the PDF from existing files.")
parser.add_argument('--only-scrape-metadata', action='store_true', help="Similar to --skip-scrape, but only scrape the metadata.")
parser.add_argument('--skip-ocr', action='store_true', help="Don't do any OCR.")
parser.add_argument('--compress', action='store_true', help="Run compression and optimization. Probably won't do anything as there isn't much more compression that can be done.")
args = parser.parse_args()

args.output = Path(args.output)
args.output.mkdir(exist_ok=True, parents=True)
# ebook_output = args.output / f'{args.isbn}.pdf'
ebook_files = args.output / args.isbn
ebook_files.mkdir(exist_ok=True, parents=True)

book_info = {}
non_number_pages = 0

platform_identifiers = {
    'home_url': "https://reader.yuzu.com",
    'jigsaw_url' "https://jigsaw.yuzu.com"
    'total_pages': "sc-gFSQbh ognVW",
    'current_page': "InputControl__input-fbzQBk hDtUvs TextField__InputControl-iza-dmV iISUBf",
    'page_loader': "sc-hiwPVj hZlgDU",
    'next_page': "IconButton__button-bQttMI cSDGGI",
    } if args.yuzu else {
    'home_url': "https://bookshelf.vitalsource.com",
    'jigsaw_url' "https://jigsaw.vitalsource.com"
    'total_pages': "sc-knKHOI gGldJU",
    'current_page': "InputControl__input-fbzQBk hDtUvs TextField__InputControl-iza-dmV iISUBf",
    'page_loader': "sc-AjmGg dDNaMw",
    'next_page': "IconButton__button-bQttMI gHMmeA sc-oXPCX mwNce",
}




def get_num_pages():
    while True:
        try:
            total = int(driver.execute_script('return document.getElementsByClassName("'+platform_identifiers['total_pages']+'")[0].innerHTML').strip().split('/')[-1].strip())
            try:
                # Get the value of the page number textbox
                current_page = driver.execute_script('return document.getElementsByClassName("'+platform_identifiers['current_page']+'")[0].value')
                if current_page == '' or not current_page:
                    # This element may be empty so just set it to 0
                    current_page = 0
            except selenium.common.exceptions.JavascriptException:
                current_page = 0
            return current_page, total
        except selenium.common.exceptions.JavascriptException:
            time.sleep(1)


def load_book_page(page_id):
    driver.get(platform_identifiers['home_url']+'/reader/books/{args.isbn}/pageid/{page_id}')
    get_num_pages()  # Wait for the page to load
    # Wait for the page loader animation to disappear
    while len(driver.find_elements(By.CLASS_NAME, platform_identifiers['page_loader'])):
        time.sleep(1)


if not args.skip_scrape or args.only_scrape_metadata:
    chrome_options = webdriver.ChromeOptions()
    if args.disable_web_security:
        chrome_options.add_argument('--disable-web-security')
        print('DISABLED WEB SECURITY!')
    chrome_options.add_argument('--disable-http2')  # VitalSource's shit HTTP2 server is really slow and will sometimes send bad data.
    if args.chrome_exe:
        chrome_options.binary_location = args.chrome_exe  # '/usr/bin/google-chrome'
    seleniumwire_options = {
        'disable_encoding': True  # Ask the server not to compress the response
    }
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), chrome_options=chrome_options, seleniumwire_options=seleniumwire_options)

    driver.get(platform_identifiers['home_url'])
    input('Press ENTER once logged in...')

    driver.maximize_window()
    page_num = args.start_page
    load_book_page(page_num)

    # Get book info
    print('Scraping metadata...')
    time.sleep(args.delay * 2)
    failed = True
    for i in range(5):
        for request in driver.requests:
            if request.url == platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/pages':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get pages information.')
                else:
                    book_info['pages'] = json.loads(request.response.body.decode())
            elif request.url == platform_identifiers['jigsaw_url']+f'/info/books.json?isbns={args.isbn}':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get book information.')
                else:
                    book_info['book'] = json.loads(request.response.body.decode())
            elif request.url == platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/toc':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get TOC information, only got:', list(book_info.keys()))
                else:
                    book_info['toc'] = json.loads(request.response.body.decode())
        if 'pages' not in book_info.keys() or 'book' not in book_info.keys() or 'toc' not in book_info.keys():
            print('Missing some book data, only got:', list(book_info.keys()))
        else:
            failed = False
        if not failed:
            break
        print('Retrying metadata scrape in 10s...')
        load_book_page(page_num)
        time.sleep(10)

    if args.only_scrape_metadata:
        driver.close()
        del driver

    if not args.only_scrape_metadata:
        _, total_pages = get_num_pages()

        if args.start_page > 0:
            print('You specified a start page so ignore the very large page count.')
        total_pages = 99999999999999999 if args.start_page > 0 else total_pages

        print('Total number of pages:', total_pages)
        print('Scraping pages...')

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
                        if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
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
                    non_number_pages += 1
                    bar.write(f'Non-number page {page}, increasing page count by 1 to: {total_pages}')
                    bar.total = total_pages
                    bar.refresh()

            if page_num == args.end_page:
                bar.write(f'Exiting on page {page_num}.')
                break

            # On the first page the back arrow is disabled and will trigger this
            if isinstance(page_num, int) and page_num > 0:
                try:
                    # If a page forward/backwards button is disabled
                    if driver.execute_script(f'return document.getElementsByClassName("'+
                                             platform_identifiers['next_page']+'")[0].disabled'):
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
                        if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
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
            bar.update(1)
        bar.close()

        time.sleep(1)
        print('All pages scraped! Now downloading images...')

        bar = tqdm(total=len(page_urls))
        for page, base_url in page_urls:
            success = False
            for retry in range(6):
                del driver.requests
                time.sleep(args.delay / 2)
                driver.get(f'{base_url.strip("/")}/2000')
                time.sleep(args.delay / 2)
                retry_delay = 5
                img_data = None
                for page_retry in range(3):  # retry the page max this many times
                    largest_size = 0
                    for find_img_retry in range(3):
                        for request in driver.requests:
                            if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
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
    print('Page scrape skipped...')

# Sometimes the book skips a page. Add a blank page if thats the case.
print('Checking for blank pages...')
existing_page_files = move_romans_to_front(roman_sort_with_ints([try_convert_int(str(x.stem)) for x in list(ebook_files.iterdir())]))
if non_number_pages == 0:  # We might not have scraped so this number needs to be updated.
    for item in existing_page_files:
        if isinstance(try_convert_int(item), str):
            non_number_pages += 1
for page in tqdm(iterable=existing_page_files):
    page_i = try_convert_int(page)
    if isinstance(page_i, int) and page_i > 0:
        page_i += non_number_pages
        last_page_i = try_convert_int(existing_page_files[page_i - 1])
        if isinstance(last_page_i, int):
            last_page_i = last_page_i + non_number_pages
            if last_page_i != page_i - 1:
                img = Image.new('RGB', (2000, 2588), (255, 255, 255))
                img.save(ebook_files / f'{int(page) - 1}.jpg')
                tqdm.write(f'Created blank image for page {int(page) - 1}.')

print('Building PDF...')
raw_pdf_file = args.output / f'{args.isbn} RAW.pdf'
existing_page_files = move_romans_to_front(roman_sort_with_ints([try_convert_int(str(x.stem)) for x in list(ebook_files.iterdir())]))
page_files = [str(ebook_files / f'{x}.jpg') for x in existing_page_files]
pdf = img2pdf.convert(page_files)
with open(raw_pdf_file, 'wb') as f:
    f.write(pdf)

if 'book' in book_info.keys() and 'books' in book_info['book'].keys() and len(book_info['book']['books']):
    title = book_info['book']['books'][0]['title']
    author = book_info['book']['books'][0]['author']
else:
    title = args.isbn
    author = 'Unknown'

if not args.skip_ocr:
    print('Running OCR...')
    ocr_in = raw_pdf_file
    _, raw_pdf_file = tempfile.mkstemp()
    subprocess.run(f'ocrmypdf -l {args.language} --title "{title}" --jobs $(nproc) --output-type pdfa "{ocr_in}" "{raw_pdf_file}"', shell=True)
else:
    ebook_output_ocr = args.output / f'{args.isbn}.pdf'
    print('Skipping OCR...')

# Add metadata
print('Adding metadata...')
file_in = open(raw_pdf_file, 'rb')
pdf_reader = PdfReader(file_in)
pdf_merger = PdfMerger()
pdf_merger.append(file_in)

pdf_merger.add_metadata({'/Author': author, '/Title': title, '/Creator': f'ISBN: {args.isbn}'})

if 'toc' in book_info.keys():
    print('Creating TOC...')
    for item in book_info['toc']:
        pdf_merger.add_outline_item(item['title'], int(item['cfi'].strip('/')) - 1)
else:
    print('Not creating TOC...')

_, tmpfile = tempfile.mkstemp()
pdf_merger.write(open(tmpfile, 'wb'))

romans_end = 0
for p in existing_page_files:
    if isinstance(p, str):
        romans_end += 1

if romans_end > 0:
    print('Renumbering pages...')
    reader = pdfrw_reader(tmpfile)
    labels = PageLabels.from_pdf(reader)

    roman_labels = PageLabelScheme(
        startpage=0,
        style='none',
        prefix='Cover',
        firstpagenum=1
    )
    labels.append(roman_labels)

    roman_labels = PageLabelScheme(
        startpage=1,
        style='roman lowercase',
        firstpagenum=1
    )
    labels.append(roman_labels)

    normal_labels = PageLabelScheme(
        startpage=romans_end,
        style='arabic',
        firstpagenum=1
    )
    labels.append(normal_labels)

    labels.write(reader)
    writer = pdfrw_writer()
    writer.trailer = reader
    writer.write(args.output / f'{title}.pdf')
else:
    shutil.move(tmpfile, args.output / f'{title}.pdf')

os.remove(tmpfile)

if args.compress:
    print('Compressing PDF...')
    # https://pypdf2.readthedocs.io/en/latest/user/file-size.html
    reader = PdfReader(args.output / f'{title}.pdf')
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()  # This is CPU intensive!
        writer.add_page(page)
    with open(args.output / f'{title} compressed.pdf', 'wb') as f:
        writer.write(f)
