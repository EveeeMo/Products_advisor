import yfinance as yf
import pandas as pd
from datetime import datetime
from tqdm import tqdm  # 添加进度条

def get_top_performers(start_date='2024-01-01', top_n=10):
    # 获取纳斯达克100的成分股（作为示例）
    print("正在获取纳斯达克100成分股列表...")
    nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
    tickers = nasdaq100['Ticker'].tolist()
    
    results = []
    print("正在获取各股票数据...")
    for ticker in tqdm(tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date)
            
            if len(hist) > 0:
                initial_price = hist.iloc[0]['Close']
                current_price = hist.iloc[-1]['Close']
                gain = ((current_price - initial_price) / initial_price) * 100
                
                results.append({
                    'Ticker': ticker,
                    'Company': stock.info.get('longName', 'N/A'),
                    'Gain (%)': round(gain, 2),
                    'Initial Price': round(initial_price, 2),
                    'Current Price': round(current_price, 2)
                })
        except Exception as e:
            print(f"\nError processing {ticker}: {str(e)}")
    
    # 将结果转换为DataFrame并排序
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Gain (%)', ascending=False)
    
    return df_results.head(top_n)

if __name__ == "__main__":
    print("获取2024年初至今涨幅最大的美股...")
    top_stocks = get_top_performers()
    print("\n涨幅最大的10支股票：")
    print(top_stocks.to_string(index=False)) 