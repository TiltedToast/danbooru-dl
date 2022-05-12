import json
import multiprocessing
import os
import shutil
import sys
import time
from queue import Queue
from threading import Thread
from urllib.parse import quote_plus

import click
import requests
from bs4 import BeautifulSoup
from progress.bar import Bar


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS

    except Exception:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)


BASE_URL = "http://danbooru.donmai.us"
posts = []
total_queue_size = 0


def download_url(url: str, save_location: str):
    r = requests.get(url, stream=True, timeout=10, headers={"User-agent": "Mozilla/5.0"})
    with open(save_location, "wb") as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)


class DownloadWorker(Thread):
    global dl_bar

    def __init__(self, queue: Queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            url, save_location = self.queue.get()
            try:
                download_url(url, save_location)
                dl_bar.next()
            finally:
                self.queue.task_done()


class DownloadWorker2(Thread):
    global posts

    def __init__(self, queue2: Queue):
        Thread.__init__(self)
        self.queue = queue2

    def run(self):

        while True:
            i, tag, safe, risky, explicit = self.queue.get()
            try:
                r = requests.get(f"{BASE_URL}/posts.json?page={i + 1}&tags={tag}")
                if r.status_code == 200:
                    data = json.loads(r.text)
                    for post in data:
                        if post not in posts:
                            if (
                                (safe and post["rating"] == "s")
                                or (risky and post["rating"] == "q")
                                or (explicit and post["rating"] == "e")
                            ):
                                posts.append(post)
            finally:
                pages_bar.next()
                self.queue.task_done()


def add_posts_to_list(page_amount_total, tag, safe, risky, explicit):
    global posts, pages_bar

    thread_count = multiprocessing.cpu_count()
    queue = Queue()
    pages_bar = Bar(f"Adding {page_amount_total} pages worth of posts to queue", max=page_amount_total)

    for _ in range(thread_count):
        worker = DownloadWorker2(queue)
        worker.daemon = True
        worker.start()

    j = 0
    for i in range(int(page_amount_total)):
        queue.put((i, tag, safe, risky, explicit))
        j += 1

    queue.join()
    pages_bar.finish()
    return posts


@click.command()
@click.option("--tag", "-t", prompt="Tag", help="Tag to search for")
@click.option(
    "--output",
    "-o",
    prompt="Output Directory",
    help="Output Directory, defaults to output folder in " "current directory",
    default="output",
)
@click.option("-safe", prompt="Safe", help="Safe, defaults to true", default=True)
@click.option("-risky", prompt="Risky", help="Risky, defaults to false", default=False)
@click.option("-explicit", prompt="Explicit", help="Explicit, defaults to false", default=False)
def main(tag: str, output: str = "output", safe: str = True, risky=False, explicit: str = False):
    global dl_bar, total_queue_size
    """
    Search Danbooru for images with a given tag and download them to the output directory
    """
    r = requests.get(BASE_URL + f"/posts?tags={quote_plus(tag)}")
    soup = BeautifulSoup(r.text, "html.parser")

    navbar_nums = soup.find_all("a", class_="paginator-page desktop-only")

    try:
        page_amount_total = int(navbar_nums[-1].text)
    except IndexError:
        click.echo("This is not a valid tag!")
        return

    os.mkdir(output) if not os.path.isdir(output) else None

    posts = add_posts_to_list(page_amount_total, tag, safe, risky, explicit)
    thread_count = multiprocessing.cpu_count()
    queue = Queue()

    for _ in range(thread_count):
        worker = DownloadWorker(queue)
        worker.daemon = True
        worker.start()

    for post in posts:
        try:
            if safe and post["rating"] == "s" and not os.path.exists(f"{output}/safe/{post['id']}.{post['file_ext']}"):
                if not os.path.isdir(f"{output}/safe"):
                    os.mkdir(f"{output}/safe")

                queue.put((post["file_url"], f"{output}/safe/{post['id']}.{post['file_ext']}"))
                total_queue_size += 1

            elif (
                risky
                and post["rating"] == "q"
                and not os.path.exists(f"{output}/risky/{post['id']}.{post['file_ext']}")
            ):
                if not os.path.isdir(f"{output}/risky"):
                    os.mkdir(f"{output}/risky")

                queue.put((post["file_url"], f"{output}/risky/{post['id']}.{post['file_ext']}"))
                total_queue_size += 1

            elif (
                explicit
                and post["rating"] == "e"
                and not os.path.exists(f"{output}/explicit/{post['id']}.{post['file_ext']}")
            ):
                if not os.path.isdir(f"{output}/explicit"):
                    os.mkdir(f"{output}/explicit")

                queue.put((post["file_url"], f"{output}/explicit/{post['id']}.{post['file_ext']}"))
                total_queue_size += 1
        except KeyError:
            continue

    start_time = time.time()

    dl_bar = Bar(
        f"Downloading {total_queue_size} posts", max=total_queue_size, suffix="%(index)d/%(max)d (%(percent).2f%%)"
    )
    queue.join()
    dl_bar.finish()

    click.echo(f"Finished downloading after {round(time.time() - start_time, 2)} seconds")


if __name__ == "__main__":
    main()
