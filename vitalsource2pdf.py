import argparse
import time
from pathlib import Path

import selenium
from PIL import Image
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
# from webdriver_manager.firefox import GeckoDriverManager
# from selenium.webdriver.firefox.service import Service as FirefoxService
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='./VitalSource/')
parser.add_argument('--isbn', required=True)
parser.add_argument('--delay', default=2, type=int, help='Delay between pages to let them load in seconds.')
parser.add_argument('--pages', default=None, type=int, help='Override how many pages to save.')  # TODO
parser.add_argument('--start-page', default=0, type=int, help='Start on this page. Pages start at zero and include any non-numbered pages.')
parser.add_argument('--disable-web-security', action='store_true', help="If pages aren't loading then you can try disabling CORS protections.")
args = parser.parse_args()

args.output = Path(args.output)
args.output.mkdir(exist_ok=True, parents=True)
ebook_output = args.output / f'{args.isbn}.pdf'
ebook_files = args.output / args.isbn
ebook_files.mkdir(exist_ok=True, parents=True)

options = webdriver.ChromeOptions()
options.add_experimental_option('prefs', {'download.default_directory': str(ebook_files)})
if args.disable_web_security:
    options.add_argument('--disable-web-security')
    print('DISABLED WEB SECURITY!')
options.add_argument('--disable-http2')  # VitalSource's shit HTTP2 server is really slow and will sometimes send bad data.
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), chrome_options=options)

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


page_num = args.start_page
load_book_page(page_num)

_, total_pages = get_num_pages()
print('Total number of pages:', total_pages)

page_urls = set()
failed_pages = set()
small_pages_redo = set()
bar = tqdm(total=total_pages)
bar.update(page_num)
while page_num < total_pages + 1:
    time.sleep(args.delay)
    img_data = None
    retry_delay = 5
    base_url = None
    for page_retry in range(3):  # retry the page max this many times
        largest_size = 0
        for find_img_retry in range(3):
            for request in driver.requests:
                if request.url.startswith(f'https://jigsaw.vitalsource.com/books/{args.isbn}/images/'):
                    # Wait for the image to load
                    wait = 0
                    while (not request.response or not request.response.body) and wait < 60:
                        time.sleep(1)
                        wait += 1
                    if not request.response or not request.response.body:
                        bar.write(f'Page {page_num} failed to load, will retry later. {request.url}')
                        failed_pages.add(page_num)
                        break

                    base_url = request.url.split('/')
                    try:
                        img_size = int(base_url[-1])
                    except ValueError:
                        bar.write(f'Failed to parse URL for page {page_num}, retrying later: {request.url}')
                        failed_pages.add(page_num)
                        break
                    if img_size > largest_size:
                        base_url = '/'.join(base_url)
                        img_data = request.response.body
                        page_urls.add(request.url)
                    # 2000 is the max size I've seen so we can just exit if it's that.
                    if img_size == 2000:
                        break
            time.sleep(1)
        if base_url:
            break
        bar.write(f'Could not find a matching image for page {page_num}, sleeping {retry_delay}s...')
        time.sleep(retry_delay)
        retry_delay += 5

    if not img_data:
        bar.write(f'Failed to download image for page {page_num}, retrying later.')
        failed_pages.add(page_num)
    elif not base_url:
        bar.write(f'Failed to get a URL for page {page_num}, retrying later.')
        failed_pages.add(page_num)
    else:
        page, _ = get_num_pages()
        # If this isn't a numbered page we will need to increment the page count
        try:
            int(page)
        except ValueError:
            total_pages += 1
            bar.write(f'Non-number page {page}, increasing page count by 1 to: {total_pages}')
            bar.total = total_pages
            bar.refresh()

        dl_file = ebook_files / f'{page}.jpg'
        with open(dl_file, 'wb') as file:
            file.write(img_data)

        # Re-save the image to make sure it's in the correct format
        img = Image.open(dl_file)
        if img.width != 2000:
            bar.write(f'Page {page_num} is only {img.width}px wide, will search for a larger image later.')
            small_pages_redo.add(page_num)
        img.save(dl_file, format='JPEG', subsampling=0, quality=100)
        del img

        bar.write(base_url)

    # Move to the next page
    del driver.requests
    actions = ActionChains(driver)
    actions.send_keys(Keys.RIGHT)
    actions.perform()

    bar.update()
    page_num += 1

# TODO: redo failed pages in failed_pages
# TODO:

driver.close()
bar.close()

# TODO: maybe scrape book title to name the PDF file?
# TODO: also maybe embed the title in the PDF file?

# TODO: make PDF

# TODO: scrape table of contents and insert


# TODO: https://stackoverflow.com/questions/29657237/tesseract-ocr-pdf-as-input
