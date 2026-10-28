import argparse, json
from pathlib import Path
import pandas as pd
from .core import backtest, signals

def main():
    p = argparse.ArgumentParser(description="稳盈量化 V1 research CLI")
    p.add_argument("command", choices=["validate", "screen", "backtest"])
    p.add_argument("--input", required=True, help="CSV: date,symbol,open,high,low,close,volume")
    p.add_argument("--out", default="outputs")
    args = p.parse_args()
    df = pd.read_csv(args.input, dtype={"symbol":str})
    out = Path(args.out); out.mkdir(parents=True,exist_ok=True)
    if args.command == "validate":
        from .core import validate
        x=validate(df); print(f"VALID rows={len(x)} symbols={x.symbol.nunique()}")
    elif args.command == "screen":
        x=signals(df)
        day=x.date.max()
        picks=x[(x.date==day)&(x.score>=80)].sort_values("score",ascending=False)
        picks.to_csv(out/"candidates.csv",index=False)
        print(f"SCREEN {day.date()}: {len(picks)} candidates -> {out/'candidates.csv'}")
    else:
        eq,tr,summary=backtest(df)
        eq.to_csv(out/"equity.csv",index=False); tr.to_csv(out/"trades.csv",index=False)
        (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
        print(json.dumps(summary,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
