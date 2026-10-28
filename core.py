"""Research-only daily-bar baseline. Signals on close t, execution at open t+1."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

REQUIRED = {"date", "symbol", "open", "high", "low", "close", "volume"}


def validate(df):
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    x = df.copy()
    x["date"] = pd.to_datetime(x["date"])
    x["symbol"] = x["symbol"].astype(str).str.zfill(6)
    x = x.sort_values(["symbol", "date"]).reset_index(drop=True)
    if x.duplicated(["symbol", "date"]).any():
        raise ValueError("duplicate symbol/date")
    if (x[["open", "high", "low", "close"]] <= 0).any().any() or (x["volume"] < 0).any():
        raise ValueError("invalid OHLCV")
    if ((x.high < x[["open", "close", "low"]].max(axis=1)) | (x.low > x[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("inconsistent OHLC")
    return x


def signals(df):
    x = validate(df)
    g = x.groupby("symbol", group_keys=False)
    x["ma5"] = g.close.transform(lambda s: s.rolling(5, min_periods=5).mean())
    x["ma20"] = g.close.transform(lambda s: s.rolling(20, min_periods=20).mean())
    x["vol5"] = g.volume.transform(lambda s: s.rolling(5, min_periods=5).mean())
    x["prev20high"] = g.close.transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    x["momentum5"] = g.close.transform(lambda s: s.pct_change(5))
    x["score"] = ((x.close > x.ma20).astype(int)*30 + (x.ma5 > x.ma20).astype(int)*20 +
                  (x.close > x.prev20high).astype(int)*30 + (x.volume > x.vol5).astype(int)*20)
    x.loc[x.ma20.isna() | x.prev20high.isna(), "score"] = 0
    return x

@dataclass
class Settings:
    initial_cash: float = 100000
    risk_fraction: float = .01
    max_allocation: float = .20
    stop_fraction: float = .05
    hold_days: int = 3
    commission: float = .0003
    min_commission: float = 5.0
    sell_tax: float = .0005  # illustrative; verify against trade date
    slippage: float = .001
    max_month_drawdown: float = .05
    max_losing_trades: int = 3


def backtest(df, cfg=Settings()):
    """Daily open execution, 100-share lots, T+1, 1-3 trading-day hold.

    Research simplifications: single position, no auction queue model, no corporate actions
    (input must be consistently adjusted), no suspension/limit-price fill guarantee.
    """
    x = signals(df)
    dates = sorted(x.date.unique())
    byday = {d: z.set_index("symbol") for d,z in x.groupby("date")}
    cash = float(cfg.initial_cash)
    position = None
    equity = []
    trades = []
    pending = None
    month_peak = cfg.initial_cash
    month = None
    losing_streak = 0
    for day in dates:
        rows = byday[day]
        if month != pd.Timestamp(day).to_period("M"):
            month = pd.Timestamp(day).to_period("M")
            month_peak = cash + (position["shares"]*position["last_close"] if position else 0)
        if position:
            symbol = position["symbol"]
            if symbol in rows.index:
                bar = rows.loc[symbol]
                position["last_close"] = float(bar.close)
                position["age"] += 1
                # sell at open after prior-close signal, never on same-day entry
                if position.get("exit_next_open"):
                    proceeds = position["shares"]*float(bar.open)*(1-cfg.slippage)
                    fee = max(cfg.min_commission, proceeds*cfg.commission) + proceeds*cfg.sell_tax
                    cash += proceeds-fee
                    pnl = proceeds-fee-position["cost"]
                    trades.append({"symbol":symbol,"entry":str(position["entry"].date()),"exit":str(pd.Timestamp(day).date()),"pnl":round(pnl,2)})
                    losing_streak = losing_streak+1 if pnl < 0 else 0
                    position = None
                elif position["age"] >= cfg.hold_days or float(bar.close) <= position["entry_price"]*(1-cfg.stop_fraction):
                    position["exit_next_open"] = True
            # missing bars: keep position, no invented fill
        if position is None and pending and pending in rows.index:
            bar = rows.loc[pending]
            if float(bar.volume) > 0:
                entry_price = float(bar.open)*(1+cfg.slippage)
                budget = min(cash*cfg.max_allocation, cfg.initial_cash*cfg.risk_fraction/cfg.stop_fraction)
                shares = int(budget//(entry_price*100))*100
                gross = shares*entry_price
                fee = max(cfg.min_commission, gross*cfg.commission) if shares else 0
                if shares > 0 and gross+fee <= cash:
                    cash -= gross+fee
                    position = {"symbol":pending,"shares":shares,"entry_price":entry_price,"cost":gross+fee,"entry":pd.Timestamp(day),"age":0,"last_close":float(bar.close),"exit_next_open":False}
        pending = None
        total = cash + (position["shares"]*position["last_close"] if position else 0)
        month_peak = max(month_peak,total)
        equity.append({"date":pd.Timestamp(day).date().isoformat(),"equity":round(total,2),"cash":round(cash,2)})
        # selection after close, trade next session at open; halt on monthly drawdown / losing streak
        if position is None and total >= month_peak*(1-cfg.max_month_drawdown) and losing_streak < cfg.max_losing_trades:
            candidates = rows[(rows.score >= 80) & (rows.volume > 0)]
            if not candidates.empty:
                pending = candidates.sort_values(["score","momentum5"],ascending=False).index[0]
    eq = pd.DataFrame(equity)
    tr = pd.DataFrame(trades, columns=["symbol","entry","exit","pnl"])
    returns = eq.equity.pct_change().fillna(0)
    dd = eq.equity/eq.equity.cummax()-1
    summary = {"start":eq.date.iloc[0],"end":eq.date.iloc[-1],"initial_cash":cfg.initial_cash,
               "ending_equity":float(eq.equity.iloc[-1]),"total_return":float(eq.equity.iloc[-1]/cfg.initial_cash-1),
               "max_drawdown":float(dd.min()),"closed_trades":len(tr),
               "win_rate":float((tr.pnl>0).mean()) if len(tr) else None,
               "daily_return_std":float(returns.std())}
    return eq,tr,summary
