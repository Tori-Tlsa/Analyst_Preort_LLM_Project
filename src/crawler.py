"""
Report Crawler Module
웹에서 리포트를 크롤링하고 PDF를 다운로드하는 기능
"""

import pandas as pd
import requests
import os
import datetime
import io
from bs4 import BeautifulSoup
from urllib.request import urlopen


def progressBar(value, endvalue, bar_length=20):
    """진행률 표시 함수"""
    percent = float(value) / endvalue
    arrow = '-' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    print("\rPercent: [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))), end='')


def naver_crawler(crpname, start_date='20090101', end_date='20190630'):
    """
    Naver Finance에서 종목 리포트 정보 크롤링
    
    Args:
        crpname: 기업명 (예: '삼성전자')
        start_date: 시작 날짜 (YYYYMMDD 형식)
        end_date: 종료 날짜 (YYYYMMDD 형식)
    
    Returns:
        DataFrame: [date, kapital, title, comment, price, pdf]
    """
    print(f'\n----- crawling {crpname} -----')
    start = datetime.datetime.now()

    # 종목 코드 가져오기
    url_krx = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
    res = requests.get(url_krx)
    res.encoding = 'euc-kr'
    code_df = pd.read_html(io.StringIO(res.text), header=0)[0]
    code_df['종목코드'] = code_df['종목코드'].apply(pd.to_numeric, errors='coerce')
    code_df = code_df.dropna(subset=['종목코드'])
    code_df['종목코드'] = code_df['종목코드'].astype(int).map('{:06d}'.format)

    # 종목 코드 추출
    try:
        itemCode = code_df.query(f"회사명 == '{crpname}'")['종목코드'].values[0]
    except IndexError:
        raise ValueError(f"종목명 '{crpname}'에 해당하는 코드를 찾을 수 없습니다.")

    # 리포트 크롤링
    url = f'https://finance.naver.com/research/company_list.nhn?searchType=itemCode&itemCode={itemCode}&page='
    headers = {'User-Agent': 'Mozilla/5.0'}
    idx_list = [2,3,4,5,6,10,11,12,13,14,18,19,20,21,22,26,27,28,29,30,34,35,36,37,38,42,43,44,45,46]
    records = []

    for page in range(1, 26):
        progressBar(page, 25)
        r = requests.get(url + str(page), headers=headers)
        r.encoding = 'euc-kr'
        source = BeautifulSoup(r.text, 'html.parser')
        srlists = source.find_all('tr')

        for i in range(30):
            try:
                tr = srlists[idx_list[i]]
                date = '20' + tr.find_all('td')[4].text.replace('.', '')
                if date < start_date:
                    return pd.DataFrame(records, columns=['date','kapital','title','comment','price','pdf'])

                kap = tr.find_all('td')[2].text
                pdf = tr.find_all('td')[3].find('a')['href'][-17:-4]
                href = 'https://finance.naver.com/research/' + tr.find_all('td')[1].find('a')['href']
                html2 = urlopen(href)
                sour2 = BeautifulSoup(html2.read(), "html.parser")
                comment = sour2.find_all("em")[2].text.replace('매수','Buy')
                price = sour2.find_all("em")[1].text.replace('원','')
                title_raw = sour2.find_all("th")[0]
                a1 = str(title_raw).find('span')
                a2 = len(str(title_raw.find('span')))
                b1 = str(title_raw).find(str(title_raw.find('p')))
                title = str(title_raw)[a1+a2:b1].replace('\n','').replace('\t','')
                records.append([date, kap, title, comment, price, pdf])
            except:
                continue

    end = datetime.datetime.now()
    print('\n---- crawling TIME:', end - start)
    return pd.DataFrame(records, columns=['date','kapital','title','comment','price','pdf'])


def pdf_download(df_pdf, pdfpath):
    """
    PDF 파일 다운로드
    
    Args:
        df_pdf: PDF ID 리스트
        pdfpath: 저장 경로
    """
    print('\n.....downloading <%d> pdf files.....' % len(df_pdf))
    os.makedirs(pdfpath, exist_ok=True)
    url = 'https://ssl.pstatic.net/imgstock/upload/research/company/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for idx, pdf in enumerate(df_pdf):
        # 숫자로 시작하지 않으면 skip
        if not str(pdf)[0].isdigit():
            continue

        fname = os.path.join(pdfpath, f"{pdf}.pdf")
        if not os.path.exists(fname):
            try:
                r = requests.get(url + f"{pdf}.pdf", headers=headers)
                with open(fname, 'wb') as f:
                    f.write(r.content)
            except:
                print(f"Failed to download: {pdf}")
        progressBar(idx+1, len(df_pdf))
