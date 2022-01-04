import json
import multiprocessing.pool
import typing
import requests
import shutil
import os
import sys
import click
from time import sleep
import selenium.common
import numpy as np
from queue import Queue
from threading import Thread
from urllib.parse import quote_plus
from multiprocessing import Pool
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS

    except Exception:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)


driver_path = "driver/chromedriver.exe"
BASE_URL = "http://danbooru.donmai.us"


def download_url(url: str, save_location: str):
    r = requests.get(url, stream=True, timeout=10, headers={'User-agent': 'Mozilla/5.0'})
    with open(save_location, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)


def add_posts_to_list(page_amount_total, tag):
    j = 0
    posts = []
    for i in range(int(page_amount_total)):
        r = requests.get(f"{BASE_URL}/posts.json?page={i + 1}&tags={tag}")
        if r.status_code == 200:
            data = json.loads(r.text)
            for post in data:
                if post not in posts:
                    posts.append(post)
                    click.echo(f"Added Post #{j + 1} to the queue")
                    j += 1

    return posts


@click.command()
@click.option("--tag", "-t", prompt="Tag", help="Tag to search for")
@click.option("--output", "-o", prompt="Output Directory", help="Output Directory, defaults to output folder in "
                                                                "current directory", default="output")
@click.option("-safe", prompt="Safe", help="Safe, defaults to true", default=True)
@click.option("-risky", prompt="Risky", help="Risky, defaults to false", default=False)
@click.option("-explicit", prompt="Explicit", help="Explicit, defaults to false", default=False)
def main(tag: str, output: str = "output", safe: str = True, risky=False, explicit: str = False):
    """
    Search Danbooru for images with a given tag and download them to the output directory
    """

    chrome_service = Service(resource_path(driver_path))
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(BASE_URL + f"/posts?tags={quote_plus(tag)}")

    navbar_nums = driver.find_elements(By.CLASS_NAME, "paginator-page.desktop-only")
    try:
        page_amount_total = navbar_nums[-1].text
    except IndexError:
        click.echo("This is not a valid tag!")
        driver.close()
        return
    driver.close()

    os.mkdir(output) if not os.path.isdir(output) else None

    for i in range(int(page_amount_total)):
        r = requests.get(f"{BASE_URL}/posts.json?page={i + 1}&tags={tag}")
        if r.status_code == 200:
            data = json.loads(r.text)

            try:
                for post in data:
                    # Download SFW Images
                    if safe and post["rating"] == "s" and not os.path.exists(f"{output}/safe/{post['id']}.{post['file_ext']}"):
                        if not os.path.isdir(f"{output}/safe"):
                            os.mkdir(f"{output}/safe")
                        download_url(post["file_url"], f"{output}/safe/{post['id']}.{post['file_ext']}")
                        click.echo(f"[SAFE] Downloaded {post['id']}.{post['file_ext']}")

                        # Download Risky Images
                    elif risky and post["rating"] == "q" and not os.path.exists(
                            f"{output}/risky/{post['id']}.{post['file_ext']}"):
                        if not os.path.isdir(f"{output}/risky"):
                            os.mkdir(f"{output}/risky")
                        download_url(post["file_url"], f"{output}/risky/{post['id']}.{post['file_ext']}")
                        click.echo(f"[RISKY] Downloaded {post['id']}.{post['file_ext']}")

                        # Download Explicit Images
                    elif explicit and post["rating"] == "e" and not os.path.exists(
                            f"{output}/explicit/{post['id']}.{post['file_ext']}"):
                        if not os.path.isdir(f"{output}/explicit"):
                            os.mkdir(f"{output}/explicit")
                        download_url(post["file_url"], f"{output}/explicit/{post['id']}.{post['file_ext']}")
                        click.echo(f"[EXPLICIT] Downloaded {post['id']}.{post['file_ext']}")

            except KeyError:
                pass


if __name__ == "__main__":
    main()
