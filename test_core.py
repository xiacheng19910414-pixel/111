import pandas as pd
import pytest
from wenying.core import validate, signals, backtest

def sample():
    dates=pd.bdate_range("2026-01-01",periods=60)
    return pd.DataFrame([{"date":d,"symbol":s,"open":p,"high":p*1.02,"low":p*.98,"close":p*1.01,"volume":100000+i*1000} for s in ["000001","000002"] for i,d in enumerate(dates) for p in [10+i*.12]])

def test_validate():
    assert len(validate(sample()))==120
    with pytest.raises(ValueError): validate(sample().drop(columns="close"))

def test_no_warmup_signal():
    assert (signals(sample()).groupby("symbol").head(20).score==0).all()

def test_backtest():
    eq,tr,s=backtest(sample())
    assert len(eq)==60 and s["initial_cash"]==100000 and s["ending_equity"]>0
