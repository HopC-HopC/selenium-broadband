from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    ElementNotVisibleException,
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep
from selenium.webdriver.support import expected_conditions as EC
import json

"""
Creating class for Provider and individual deals
"""


class Provider:
    name = str
    deals_page = str
    deals = []
    results = {}

    def __init__(self, name, deals_page):
        self.name = name
        self.deals_page = deals_page
        self.deals = []
        self.results = {}

    """
    ShowResults method to display results in a dict once complete.
    Could switch to json.
    """

    def ShowResults(self):
        self.results = {"Provider": self.name}
        for num, deal in enumerate(self.deals):
            self.results[f"Deal {num+1}"] = deal.__dict__
        print(self.results)


class BroadbandDeal:
    name = str
    price = float
    speed = str
    set_up_cost = float
    contract_length = int

    def __init__(self, name, price, speed, set_up_cost, contract_length):
        self.name = name
        self.price = price
        self.speed = speed
        self.set_up_cost = set_up_cost
        self.contract_length = contract_length

    """
    building in a toJSON method
    """

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)


"""
Creating instances of Provider class for both BT and Hyperoptic, including provider name and URLs
"""
bt = Provider(name="BT", deals_page="https://www.bt.com/products/broadband/deals")
hyperoptic = Provider(
    name="Hyperoptic", deals_page="https://www.hyperoptic.com/price-plans/"
)

"""
creating some key objects for selenium
"""
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome("/Users/chris/Python/ApTap/chromedriver", options=options)
actions = ActionChains(driver)

""" 
post code could be taken from input, HTTP, API
"""
POST_CODE = "kt12ne"


def Hyperoptic_Scrape(post_code):
    driver.get(hyperoptic.deals_page)

    """
    clearing cookie popup
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, '//button[@class="modal-button accept"]')
            )
        )
    except (TimeoutError, NoSuchElementException):
        return {"error": "page not as expected"}
    driver.find_element(By.XPATH, '//button[@class="modal-button accept"]').click()

    """
    finding broadband packages. package_wrapper contains all deals, packages is a list of 
    the individual broadband deal div webelements.
    """
    package_wrapper = driver.find_element(
        By.XPATH, '//div[starts-with(@class, "packages-wr")]'
    )
    packages = package_wrapper.find_elements_by_xpath("./div")

    """
    for loop through each broadband deal div (package). 
    selecting all needed data points, parsing data where necessary.
    data is then put into a BroadbandDeal object and added to a
    list of deals belonging to the hyperoptic Provider object.
    """
    for package in packages:
        image = package.find_element(
            By.CSS_SELECTOR, "div.package-icon-wr img"
        )  # [contains(@src, 'icon')]
        name = image.get_attribute("src").split("-")[3]
        price = package.find_element(By.CSS_SELECTOR, "span.price").text
        speed = package.find_element(By.CSS_SELECTOR, "div.size-unit").text
        set_up_cost = package.find_element(
            By.CSS_SELECTOR, "span.font-f-museo-500"
        ).text
        contract_length = 24  # default; can build in check to see which contract option is selected or even loop through contract lengths for prices
        hyperoptic.deals.append(
            BroadbandDeal(
                name,
                price.replace("£", ""),
                speed.replace(" ", ""),
                "".join(
                    char
                    for char in set_up_cost.split("\n")[3].replace("£", "")
                    if char.isnumeric()
                ),
                contract_length,
            )
        )


def BT_Scrape(post_code):
    driver.get(bt.deals_page)
    """waiting for cookie popup to display"""
    sleep(8)
    """ 
    Website down for maintenance at this point!
    Testing WebDriverWait for cookie box. 
    Return to this point to replace sleep() with WebDriverWait
    """
    # WebDriverWait(driver, 15).until(
    #     EC.visibility_of_element_located((By.CLASS_NAME, "mainContent"))
    # )
    # driver.find_element(By.XPATH, "//a[contains(@class,'call')]").click()

    """ clearing cookie popup -- replace with above click() when possible"""
    actions.send_keys(
        Keys.TAB,
        Keys.ENTER,
        Keys.TAB,
        Keys.ENTER,
        Keys.TAB,
        Keys.ENTER,
    )
    actions.perform()

    """waiting for cookie popup to close to enter postcode"""
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "sc-postcode"))
        )
    except (
        TimeoutError,
        ElementNotInteractableException,
        ElementClickInterceptedException,
    ):
        return "Post code error"
    input_element = driver.find_element_by_id("sc-postcode")
    input_element.send_keys(post_code)
    input_element.send_keys(Keys.ENTER)

    """ 
    waiting for address list to show before entering arrow down and enter to submit address 
    """

    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.visibility_of_element_located((By.ID, "tvsc-address")))
    except (TimeoutException, ElementNotVisibleException):
        return {"error": "invalid address"}
    actions.reset_actions()
    actions.send_keys(
        Keys.ARROW_DOWN,
        Keys.ENTER,
        Keys.ARROW_DOWN,
        Keys.ENTER,
        Keys.ARROW_DOWN,
        Keys.ENTER,
    )
    actions.perform()
    actions.reset_actions()

    """
    post code and address submitted. product-row divs now available
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "product-rows"))
        )
    except (TimeoutException, ElementNotVisibleException):
        return {"error": "product rows not found"}

    product_row = driver.find_element_by_id("product-rows")
    product_cards = [
        product
        for product in product_row.find_elements_by_tag_name("div")
        if product.get_attribute("class") == "jss877"
    ]
    """
    At this point, all data is seperated and it is a matter of accessing individual 
    data points to create BroadbandDeal objects

    looping through product in product_cards to grab data for each broadband deal.

    once data is collected, it is used to create a BroadbandDeal object and added to
    the deals list belonging to the bt Provider object.
    """

    for product in product_cards:
        name = product.find_element_by_id("product-name")
        price = product.find_element_by_id("product-price")
        speed = product.find_element_by_class_name("jss889").text
        try:
            set_up_cost = product.find_element_by_id("upfront-section").text
        except NoSuchElementException:
            set_up_cost = product.find_element(By.ID, "upfront-cost").text
        contract_length = product.find_element_by_id("contract-length")
        bt.deals.append(
            BroadbandDeal(
                name.text,
                float(
                    price.text.replace("\\u00a3", "")
                    .replace("\\u0394", "")
                    .replace("£", "")
                    .replace("Δ", "")[:5]
                ),
                speed.split("\n")[0],
                set_up_cost.strip().replace("\\u00a", "").replace("£", ""),
                contract_length.text.split()[0],
            )
        )


if __name__ == "__main__":
    BT_Scrape(POST_CODE)
    Hyperoptic_Scrape(POST_CODE)
    bt.ShowResults()
    hyperoptic.ShowResults()
