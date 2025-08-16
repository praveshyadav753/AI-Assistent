from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Setup browser
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

wait = WebDriverWait(driver, 15)

# Go to YouTube
driver.get("https://www.youtube.com")

# Search for Tum Bin song
search_box = wait.until(EC.element_to_be_clickable((By.NAME, "search_query")))
search_box.send_keys("Tum Bin song")
search_box.send_keys(Keys.RETURN)

# Wait for first video in results and click it
first_video = wait.until(EC.element_to_be_clickable((By.XPATH, '(//a[@id="thumbnail"])[1]')))
first_video.click()

# Wait for video to load and go fullscreen
time.sleep(2)
video_player = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
video_player.send_keys("k")  # play
time.sleep(0.5)
video_player.send_keys("f")  # fullscreen
