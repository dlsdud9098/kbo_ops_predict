import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import json
import pandas as pd
from IPython.display import display

def save_file(df, path):
    df.to_csv(path, encoding='utf-8-sig', index=False)
    
def display_null_sum(df):
    for i, j in df.isnull().sum().items():
        if not j == 0:
            print(i, j)

def insert_data(regular_season, path, batter_height_weight_position):
    
    '''
    위에서 만든 데이터를 적용해서 모두 채웠다.
    '''

    def insert_batter_info(row, batter_height_weight_position):
        name = row['batter_name']
        if name in batter_height_weight_position:
            info = batter_height_weight_position[name]
            height_weight, position = info.split('/')[0] + '/' + info.split('/')[1], info.split('/')[2]
            
            row['height/weight'] = height_weight
            row['position'] = position

            # display(row[['height/weight', 'position']])
            
        return row

    # apply를 사용하여 각 행에 대해 업데이트 적용
    regular_season = regular_season.apply(insert_batter_info, axis=1, batter_height_weight_position=batter_height_weight_position)
    display(regular_season[regular_season['batter_name'] == '유재혁'][['batter_name', 'height/weight', 'position']])

    # print(regular_season.isna().sum())
    display_null_sum(regular_season)
    
    save_file(regular_season, path)

def chrome_setting():
    # Chrome 옵션 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 백그라운드 모드 실행 (필요시 주석 처리)

    # Service 객체 생성
    service = Service(ChromeDriverManager().install())

    return chrome_options, service

def init(regular_season):
    # 키와 몸무게가 있지 않은 선수 목록
    print(sorted(set(regular_season[regular_season['height/weight'].isnull()]['batter_name'])))
    null_batter_name = sorted(set(regular_season[regular_season['height/weight'].isnull()]['batter_name']))
    print(f'총 {len(null_batter_name)}')
    
    # dict 초기화
    batter_height_weight_position = {name: '' for name in null_batter_name}
        
    return batter_height_weight_position

# 크롤링 하는 코드
def crawl_start(regular_season):
    batter_height_weight_position = init(regular_season)
    chrome_options, service = chrome_setting()

    # 크롬 웹드라이버 실행
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    # 웹 페이지 로드
    driver.get('https://www.koreabaseball.com/Player/Search.aspx')

    height_weight_position_list = []
    for name in batter_height_weight_position.keys():
        
        batter_name_input = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_txtSearchPlayerName')
        try:
            batter_name_input.clear()
        except StaleElementReferenceException:
            batter_name_input = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_txtSearchPlayerName')
            batter_name_input.clear()
        batter_name_input.send_keys(name)
        driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_btnSearch').click()

        time.sleep(.5)
        height_weight = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_udpRecord > div.inquiry > table > tbody > tr > td:nth-child(6)'))).text.replace(', ','/')
        position = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_udpRecord > div.inquiry > table > tbody > tr > td:nth-child(4)').text

        
        height_weight_position_list.append(height_weight+'/'+position)
    driver.quit()
    
    return height_weight_position_list, batter_height_weight_position

def crawl_hand(regular_season, path):
    height_weight_position_list, batter_height_weight_position = crawl_start(regular_season)
    '''
    위키백과에서 투타를 가져오는데, 몇 가지 동명이인이 있어 그 부분은 넘어갔다.
    넣지 못한 부분은 일일이 넣을 예정이다.
    '''

    for idx, name in enumerate(batter_height_weight_position.keys()):
        rq = requests.get(f'https://ko.wikipedia.org/wiki/{name}')
        time.sleep(.5)
        # time.sleep(.2)
        soup = BeautifulSoup(rq.text, 'html.parser')
        try:
            handle = soup.find_all('table')[0]
            
            df = pd.read_html(str(handle))[0]
            if len(df.columns) > 2:
                df = df.drop(df.columns[2], axis=1)
            # display(df)
            df = df.T

            df.columns = df.loc[0]
            df = df.drop(0, axis=0)
            try:
                hand = str(df['투구·타석'].values[0])
            except:
                hand = ''
        except:
            hand = ''

        
        height_weight_position_list[idx] = height_weight_position_list[idx]+'('+hand+')'
        
    for idx, name in enumerate(batter_height_weight_position.keys()):
        batter_height_weight_position[name] = height_weight_position_list[idx]
        
        
    insert_data(regular_season, path, batter_height_weight_position)
    print('가져오지 못한 데이터는 일일이 넣기')
