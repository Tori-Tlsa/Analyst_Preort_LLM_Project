"""
OCR Processor Module
PDF를 텍스트로 변환하고 정제하는 기능
"""

import pandas as pd
import os
import io
import re
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams


def pdfparser(data):
    """
    PDF 파일을 텍스트로 변환
    
    Args:
        data: PDF 파일 경로
    
    Returns:
        str: 추출된 텍스트
    """
    with open(data, 'rb') as fp:
        rsrcmgr = PDFResourceManager()
        retstr = io.StringIO()
        device = TextConverter(rsrcmgr, retstr, codec='utf-8', laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)
        return retstr.getvalue()


def pdfread(pdf_dir, txt_dir):
    """
    PDF를 읽고 텍스트로 저장
    
    Args:
        pdf_dir: PDF 파일 디렉토리
        txt_dir: 텍스트 저장 디렉토리
    """
    print('\n.....reading pdf and saving txt.....')
    os.makedirs(txt_dir, exist_ok=True)
    
    for file in os.listdir(pdf_dir):
        if not file.endswith('.pdf'):
            continue
        fname_pdf = os.path.join(pdf_dir, file)
        fname_txt = os.path.join(txt_dir, file.replace('.pdf', '.txt'))
        
        if os.path.exists(fname_txt):
            continue
        
        try:
            text = pdfparser(fname_pdf)
            with open(fname_txt, 'w', encoding='utf-8') as f:
                f.write(text)
        except:
            print(f"Failed: {file}")


def extract_txt(txt_dir):
    """
    텍스트 파일을 읽고 한글만 추출 및 정제
    
    Args:
        txt_dir: 텍스트 파일 디렉토리
    
    Returns:
        DataFrame: [pdf, text]
    """
    df = pd.DataFrame(columns=['pdf', 'text'])
    
    for file in os.listdir(txt_dir):
        if not file.endswith('.txt'):
            continue
        
        with open(os.path.join(txt_dir, file), encoding='utf-8') as f:
            text = f.read()
        
        # 한글만 추출 및 공백 정제
        clean_text = re.sub('[^가-힣]', ' ', text)
        clean_text = re.sub(' +', ' ', clean_text)
        
        df = pd.concat([
            df,
            pd.DataFrame([[file.replace('.txt',''), clean_text]], columns=['pdf', 'text'])
        ], ignore_index=True)
    
    return df
