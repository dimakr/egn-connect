#!/usr/bin/env python

import logging
import os
import random
import shutil
import time
import unittest
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as exp_cond
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# pylint: disable=logging-format-interpolation
LOG_FORMAT = '[%(asctime)s] %(message)s'
logging.basicConfig(format=LOG_FORMAT,
                    level=logging.INFO)
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


# pylint: disable=missing-docstring
def log_test(func):
    def wrapped(*args, **kwargs):
        logger.info(
            "\n{larr}{sharp}[ '{test}' test ]{sharp}{rarr}".format(
                larr="<" * 5,
                sharp="#" * 25,
                test=func.__name__,
                rarr=">" * 5))
        return func(*args, **kwargs)
    return wrapped
# pylint: enable=missing-docstring


class EgnyteConnect(unittest.TestCase):
    """Basic regression tests for EgnyteConnect platform."""

    # Test and lab specific variables
    CHROMEDRIVER_PATH = ("/Users/dmitriy/Learn/Python/"
                         "egnyte_connect/chromedriver")
    TMP_DIR = "/tmp/egnyte_download"
    SHARED_FOLDER = "Dmitriy Kruglov"
    FOLDER_LINK = "https://qarecruitment.egnyte.com/fl/NTJkFNqQTx"
    PASSWORD = "ZWuzHWLW"

    def setUp(self,                     # pylint: disable=arguments-differ
              folder_link=FOLDER_LINK,
              password=PASSWORD):
        """Initializes the test environment.

        :param folder_link: str, the shared folder URL
        :param password: str, password to access the given shared folder
        :return: None
        """
        super(EgnyteConnect, self).setUp()

        self.folder_link = folder_link
        self.password = password

        # Create a local temporary directory for test purposes
        if not os.path.exists(self.TMP_DIR):
            os.makedirs(self.TMP_DIR)
        chrome_options = webdriver.ChromeOptions()
        prefs = {"download.default_directory": self.TMP_DIR}
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(self.CHROMEDRIVER_PATH,
                                       chrome_options=chrome_options)

    def tearDown(self):
        """Reset the test environment."""
        self.driver.close()
        # Remove the local temporary directory
        shutil.rmtree(self.TMP_DIR)
        super(EgnyteConnect, self).tearDown()

    def access_shared_folder(self):
        """Access the shared folder using the stored password."""
        self.driver.get(self.folder_link)
        self.assertIn("Password Protected Folder", self.driver.title)

        password_el = self.driver.find_element_by_id("password")
        password_el.send_keys(self.password)
        password_el.send_keys(Keys.RETURN)
        self.assertIn("Egnyte Connect", self.driver.title)

    @staticmethod
    def wait(func, interval=5, timeout=60):
        """Wait until result of func is True.

        :param func: callable, callable to wait for its result to be True
        :param interval: int, interval (in secs) between checks
        :param timeout: int, timeout before explicitly raising exception
        :return: None
        """
        start_time = time.time()
        while not func():
            if start_time + timeout < time.time():
                raise AssertionError(
                    "Timed out. Waited for {0} more than {1} seconds.".format(
                        func.func_name, timeout))
            time.sleep(interval)

    def wait_for_cond(self, condition, locator, tries=5):
        """Explicitly wait for the giving condition to occur.

        :param condition: callable, condition to check
        :param locator: tuple, attributes to locate the element of interest
        :param tries: int, number of tries to locate the element, in it's not
                yet completely loaded
        :return: WebElement
        """
        for i in range(1, tries + 1):
            try:
                return WebDriverWait(self.driver, 10).until(condition(locator))
            except StaleElementReferenceException:
                if i == tries:
                    raise

    # pylint: disable=invalid-name
    @log_test
    def test_access_folder_with_valid_password(self):
        """Verify that it is possible to access the shared folder
        with the provided password."""

        logger.info("Open the shared {0} link.".format(self.folder_link))
        self.driver.get(self.folder_link)
        self.assertIn(
            "Password Protected Folder",
            self.driver.title,
            msg="The access page is not opened.")

        logger.info("Enter the valid access password.")
        password_el = self.driver.find_element_by_id("password")
        password_el.send_keys(self.password)
        password_el.send_keys(Keys.RETURN)

        logger.info("Verify that shared folder is opened.")
        self.assertIn(
            "Egnyte Connect",
            self.driver.title,
            msg="The shared folder is not opened.")

    @log_test
    def test_access_folder_with_invalid_password(self):
        """Verify that accessing the shared folder with an invalid password
        is prohibited."""

        logger.info("Open the shared {0} link.".format(self.folder_link))
        self.driver.get(self.folder_link)
        self.assertIn(
            "Password Protected Folder",
            self.driver.title,
            msg="The access page is not opened.")

        logger.info("Enter an invalid access password.")
        password_el = self.driver.find_element_by_id("password")
        password_el.send_keys("{0}".format(random.randrange(1, 10000)))
        password_el.send_keys(Keys.RETURN)

        logger.info("Verify that access page is still opened.")
        self.assertIn(
            "Password Protected Folder",
            self.driver.title,
            msg="Current page is not the access one.")

        logger.info("Verify that error message is displayed "
                    "notifying user about the incorrect password.")
        err_msg_el = self.driver.find_element_by_css_selector("div.error")
        self.assertEqual(
            "Incorrect password. Try again.",
            err_msg_el.text,
            msg="'Incorrect password' error message is not displayed.")

    @log_test
    def test_download_entire_shared_folder(self):
        """Verify downloading the whole shared folder."""

        logger.info("Open the shared {0} link.".format(self.folder_link))
        self.access_shared_folder()

        logger.info("Click on 'Download Folder' button.")
        # Wait until button is available
        locator = (By.CSS_SELECTOR,
                   "button.btn.btn-primary.btn-block."
                   "folderLink-buttons-download.is-type-folder")
        download_btn = self.wait_for_cond(
            exp_cond.presence_of_element_located, locator)
        download_btn.click()

        logger.info("Verify that archived copy of the shared "
                    "folder is downloaded.")
        self.wait(lambda: os.listdir(self.TMP_DIR))
        self.assertIn("{0}.zip".format(self.SHARED_FOLDER),
                      os.listdir(self.TMP_DIR))

    @log_test
    def test_download_selected_items(self):
        """Verify downloading of selected items."""

        logger.info("Open the shared {0} link.".format(self.folder_link))
        self.access_shared_folder()

        logger.info("Select 2 items to download.")
        # Wait for loading of items list
        locator = (By.CSS_SELECTOR,
                   "#folder-items-wrapper[class='items-wrapper']")
        self.wait_for_cond(
            exp_cond.presence_of_element_located, locator)
        # Select items via checkboxes
        checkboxes = self.driver.find_elements_by_css_selector(
            "div.checkable.select-item")
        for i in (0, -1):
            checkboxes[i].click()
            checkboxes[i].is_selected()

        logger.info("Click on 'Download Folder' button.")
        download_btn = self.driver.find_element_by_css_selector(
            "button.is-type-selected")
        download_btn.click()

        logger.info("Verify that archived copy of the shared "
                    "folder is downloaded.")
        self.wait(lambda: os.listdir(self.TMP_DIR))
        self.assertIn("{0}.zip".format(self.SHARED_FOLDER),
                      os.listdir(self.TMP_DIR))

    @log_test
    def test_navigation_through_shared_folder(self):
        """Verify navigation through folders and pages (of paginated list)."""

        logger.info("Open the shared {0} link.".format(self.folder_link))
        self.access_shared_folder()

        # Loop through folders of interest
        for name in ("DataFolder1", "numbers"):
            # Wait for refresh of items list
            locator = (By.CSS_SELECTOR,
                       "#folder-items-wrapper[class='items-wrapper']")
            self.wait_for_cond(
                exp_cond.presence_of_element_located, locator)
            logger.info("Navigate to '{0}' subfolder.".format(name))
            locator = (By.CSS_SELECTOR, "span.name[title='{0}']".format(name))
            subfolder = self.wait_for_cond(
                exp_cond.element_to_be_clickable, locator)
            subfolder.click()

        # Loop through pages of interest
        for case, loc, page in (
                ["Next", "a.next", "2"],
                ["Prev", "li.prev-wrapper > a.prev", "1"],
                ["3", "a.page[data-page='3']", "3"]):
            logger.info("Navigate to the {0} page in the current "
                        "subfolder.".format(case))
            locator = (By.CSS_SELECTOR, loc)
            next_link = self.wait_for_cond(
                exp_cond.presence_of_element_located, locator)
            next_link.click()
            # Wait for loading of items list
            locator = (By.CSS_SELECTOR,
                       "#folder-items-wrapper[class='items-wrapper']")
            self.wait_for_cond(
                exp_cond.presence_of_element_located, locator)
            self.assertEqual(
                page,
                self.driver.find_element_by_css_selector(
                    "li.active span").text,
                msg="Page {0} is not displayed.".format(page))

        # Loop through folders of interest
        for case, loc, folder in (
                ["previous", "nav a.prev", "DataFolder1"],
                ["parent", "nav li.crumb-path > a.link", "Dmitriy Kruglov"],):
            logger.info("Navigate to the {0} folder.".format(case))
            locator = (By.CSS_SELECTOR, loc)
            nav_link = self.wait_for_cond(
                exp_cond.presence_of_element_located, locator)
            nav_link.click()
            # Wait navigation bar to load
            WebDriverWait(self.driver, 10).until(
                exp_cond.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "nav li.crumb-current"), folder))
            self.assertEqual(
                folder,
                self.driver.find_element_by_css_selector(
                    "nav li.crumb-current").text,
                msg="'{0}' folder is not displayed.".format(folder))
    # pylint: enable=invalid-name

if __name__ == "__main__":
    unittest.main()
