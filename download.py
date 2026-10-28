"""Optional AkShare downloader; network required. This is a starter, not full-universe archival ingestion."""
from pathlib import Path
import time
import pandas as pd

def download_daily(symbols, start="20211028", end="20261028", dest="data/raw", sleep=0.5):
    import akshare as ak
    out=Path(dest);out.mkdir(parents=True,exist_ok=True)
    errors=[]
    for symbol in symbols:
        symbol=str(symbol).zfill(6)
        path=out/f"{symbol}.csv"
        if path.exists(): continue
        try:
            df=ak.stock_zh_a_hist(symbol=symbol,period="daily",start_date=start,end_date=end,adjust="qfq")
            if df.empty: raise ValueError("empty history")
            df=df.rename(columns={"日期":"date","开盘":"open","最高":"high","最低":"low","收盘":"close","成交量":"volume"})
            df["symbol"]=symbol
            df[["date","symbol","open","high","low","close","volume"]].to_csv(path,index=False)
        except Exception as e:
            errors.append((symbol,str(e)))
        time.sleep(sleep)
    pd.DataFrame(errors,columns=["symbol","error"]).to_csv(out/"errors.csv",index=False)
    return errors
