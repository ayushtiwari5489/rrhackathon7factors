#!/usr/bin/env python3
"""
Top-10 batters and bowlers from ball-by-ball cricket data.

Inputs
  --ball-dir   folder holding the ball-by-ball CSV parts (any file matching *ball_by_ball*.csv)
  --matches    matches.csv (needs: match_id, match_date, win_team_id, man_of_the_match)

Model (original six factors = 70%, new role-specific factors = 30%)
  30%  Recent consistency        weighted mean - 0.5*std of match scores (last 10 matches, or --recent-days)
  28%  Pressure and collapse     value per ball in collapses (3+ wkts down before over 12),
                                 hard chases (RRR >= 10 after over 12) and, for bowlers, death overs
  19%  Vs all match participants average result against every opponent faced + share of opponents beaten
  11%  Opposition strength       match score adjusted by the PRIOR form of the opposing bowlers/batters
   8%  Match-winning contribution average score in won matches + Man-of-the-Match rate
   4%  Historical performance    career average match score

Every rating is on a 0-100 scale (50 = average player in the pool).
New factors (batters / bowlers)
  phase skill        value per over in powerplay / middle / death (only phases with enough balls)
  scoring quality    strike rate + boundary% + dot-ball%   |  control: dot%, boundaries conceded, extras
  pace-spin balance  results vs pace and vs spin          |  wicket-taking: wickets per 24 balls
  setting-chasing    results batting 1st vs 2nd           |  left-right balance: vs left- and right-handers
  big match          average score in knockout matches (>= 2 needed, otherwise missing, never 0)
Rules: averages not totals; small samples shrunk toward the pool mean; a match counts only if the
player really batted or bowled (no false zeros); innings 3-4 (super overs) are ignored.

Usage
  python cricket_ranking.py --ball-dir data --matches data/matches.csv
"""
import argparse
import glob
import os
import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
from cricket_dashboard import build_dashboard

# Original six factors keep 70% of the total (in their original 30/28/19/11/8/4 proportions);
# the new role-specific factors share the other 30%. Edit these numbers to change the split.
BASE = {"z_recent": 0.30, "z_pressure": 0.28, "z_vs_all": 0.19, "z_opp": 0.11, "z_win": 0.08, "z_hist": 0.04}
BASE_SHARE = 0.70
ROLE_FACTORS = {   # z column -> (output name, weight)
    "bat": {"z_phase": ("phase_skill", 0.08), "z_q": ("scoring_quality", 0.07),
            "z_x": ("pace_spin_balance", 0.06), "z_y": ("setting_chasing_balance", 0.04),
            "z_big": ("big_match", 0.05)},
    "bowl": {"z_phase": ("phase_skill", 0.08), "z_q": ("control", 0.07),
             "z_x": ("wicket_taking", 0.06), "z_y": ("left_right_balance", 0.04),
             "z_big": ("big_match", 0.05)},
}
WICKET_VALUE = 14.0   # runs a wicket is worth
K_SKILL = 150         # shrink (balls) for prior form used in opposition strength
K_PRESS = 60          # shrink (pressure balls)
SHRINK_K = {"recent": 3, "opp": 10, "win": 10, "hist": 10, "vs": 10}


# ----------------------------------------------------------------------------- loading
def load_balls(ball_dir):
    files = sorted(glob.glob(os.path.join(ball_dir, "*ball_by_ball*.csv")))
    if not files:
        sys.exit(f"No ball-by-ball files found in {ball_dir}")
    b = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)   # stacked in memory only
    n = len(b)
    # the same ball may sit in two files (e.g. an old and a new copy of a part) -> keep it once
    b = b.drop_duplicates(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    print(f"Loaded {n:,} rows from {len(files)} files; {n - len(b):,} duplicate balls removed -> {len(b):,}")
    return b


def prepare_balls(b, matches):
    b = b[b.innings.isin([1, 2])].copy()                                # drop super overs
    b = b.merge(matches[["match_id", "match_date"]], on="match_id")
    b = b.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    b["extras_type"] = b.extras_type.fillna("none")

    b["wide"] = b.extras_type.eq("wide")
    b["noball"] = b.extras_type.isin(["Overstep", "other"])
    b["legal"] = ~(b.wide | b.noball)
    b["nonwide"] = ~b.wide                                              # balls the batter faced
    b["total"] = b.runs + b.extras1_runs + b.extras_2_runs
    b["conc"] = b.runs + np.where(b.wide | b.noball, b.extras1_runs, 0)  # runs charged to bowler

    out = b.dismissed_player_id.notna() & ~b.dismissal_type.isin(["Retire Out"])
    b["dis_striker"] = out & (b.dismissed_player_id == b.striker_id)
    b["dis_nonstr"] = out & (b.dismissed_player_id == b.non_striker_id) & ~b.dis_striker
    b["bowl_wkt"] = out & ~b.dismissal_type.isin(["RunOut", "Obstracting the field", "Obstructing the field"])
    b["is_bound"] = b.is_four.astype(bool) | b.is_six.astype(bool)
    b["phase"] = np.where(b.overid <= 6, 0, np.where(b.overid <= 15, 1, 2))

    # match situation before each ball
    g = b.groupby(["match_id", "innings"])
    b["cum_runs_before"] = g.total.cumsum() - b.total
    b["cum_wk_before"] = g.dis_striker.cumsum() + g.dis_nonstr.cumsum() - b.dis_striker - b.dis_nonstr
    b["legal_before"] = g.legal.cumsum() - b.legal
    first_total = b[b.innings == 1].groupby("match_id").total.sum()
    need = b.match_id.map(first_total) + 1 - b.cum_runs_before
    balls_left = (120 - b.legal_before).clip(lower=1)
    b["rrr"] = np.where(b.innings == 2, need / balls_left * 6, 0)

    # value of every ball = result minus what an average ball gives (innings x phase)
    ex = b.groupby(["innings", "phase"]).apply(lambda x: pd.Series({
        "bat_rpb": x.runs[x.nonwide].mean(), "bat_wr": x.dis_striker[x.nonwide].mean(),
        "bowl_conc": x.conc.mean(), "bowl_wr": x.bowl_wkt.mean()}), include_groups=False)
    b = b.join(ex, on=["innings", "phase"])
    b["bat_val"] = b.runs - WICKET_VALUE * b.dis_striker - np.where(
        b.nonwide, b.bat_rpb - WICKET_VALUE * b.bat_wr, 0.0)
    b["bowl_val"] = (b.bowl_conc - b.conc) + WICKET_VALUE * (b.bowl_wkt - b.bowl_wr)

    # pressure situations
    collapse = (b.cum_wk_before >= 3) & (b.overid <= 12)
    chase = (b.innings == 2) & (b.overid >= 12) & (b.rrr >= 10) & (need > 0)
    b["bat_press"] = collapse | chase
    b["bowl_press"] = (b.overid >= 17) | chase
    return b


def add_prior_form(b, matches):
    """Opposition strength: each opponent's form from matches BEFORE the current one."""
    order = matches.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    order["ord"] = range(len(order))

    def prior(pid, val, cnt, name):
        t = b.groupby(["match_id", pid]).agg(v=(val, "sum"), n=(cnt, "sum")).reset_index()
        t = t.merge(order[["match_id", "ord"]], on="match_id").sort_values([pid, "ord"])
        pv = t.groupby(pid).v.cumsum() - t.v
        pn = t.groupby(pid).n.cumsum() - t.n
        t[name] = pv / (pn + K_SKILL)
        return t[["match_id", pid, name]]

    b = b.merge(prior("striker_id", "bat_val", "nonwide", "s_bat"), on=["match_id", "striker_id"], how="left")
    b = b.merge(prior("bowler_id", "bowl_val", "legal", "s_bowl"), on=["match_id", "bowler_id"], how="left")
    b[["s_bat", "s_bowl"]] = b[["s_bat", "s_bowl"]].fillna(0)
    b["bat_adj"] = b.bat_val + b.s_bowl     # facing a strong bowler earns credit
    b["bowl_adj"] = b.bowl_val + b.s_bat    # bowling to a strong batter earns credit
    return b


def player_match_table(b, matches):
    """One row per player per match, only where the player really batted or bowled."""
    bat_keys = pd.concat([
        b[["match_id", "striker_id", "batting_team_id"]].set_axis(["match_id", "player_id", "team_id"], axis=1),
        b[["match_id", "non_striker_id", "batting_team_id"]].set_axis(["match_id", "player_id", "team_id"], axis=1),
    ]).drop_duplicates(["match_id", "player_id"])
    bat_keys["batted"] = True
    bowl_keys = b[["match_id", "bowler_id", "bowling_team_id"]].set_axis(
        ["match_id", "player_id", "team_id"], axis=1).drop_duplicates(["match_id", "player_id"])
    bowl_keys["bowled"] = True
    pm = bat_keys.merge(bowl_keys, on=["match_id", "player_id"], how="outer", suffixes=("", "_w"))
    pm["team_id"] = pm.team_id.fillna(pm.team_id_w)
    pm = pm.drop(columns="team_id_w")
    pm[["batted", "bowled"]] = pm[["batted", "bowled"]].fillna(False).astype(bool)

    ba = b.groupby(["match_id", "striker_id"]).agg(bat_val=("bat_val", "sum"), bat_adj=("bat_adj", "sum"))
    ba = ba.rename_axis(["match_id", "player_id"]).reset_index()
    wa = b.groupby(["match_id", "bowler_id"]).agg(bowl_val=("bowl_val", "sum"), bowl_adj=("bowl_adj", "sum"))
    wa = wa.rename_axis(["match_id", "player_id"]).reset_index()
    ns = (b[b.dis_nonstr].groupby(["match_id", "non_striker_id"]).size() * -WICKET_VALUE).rename("ns_pen")
    ns = ns.rename_axis(["match_id", "player_id"]).reset_index()
    pm = pm.merge(ba, on=["match_id", "player_id"], how="left") \
           .merge(wa, on=["match_id", "player_id"], how="left") \
           .merge(ns, on=["match_id", "player_id"], how="left")
    pm = pm.fillna({"bat_val": 0, "bat_adj": 0, "bowl_val": 0, "bowl_adj": 0, "ns_pen": 0})
    pm = pm.merge(matches[["match_id", "match_date", "win_team_id", "man_of_the_match", "big"]], on="match_id")
    pm["won"] = pm.win_team_id == pm.team_id
    pm["mom"] = pm.man_of_the_match == pm.player_id
    return pm


# ----------------------------------------------------------------------------- scoring
def zscore(s):
    return ((s - s.mean()) / s.std()).clip(-3, 3)


def shrink(s, n, k):
    mu = s.mean()
    return mu + (s - mu) * n / (n + k)


def group_scores(rows, pid, val, grp, min_n, k, mode):
    """Value per over inside each group (phase, pace/spin, ...), combined per player."""
    t = rows.groupby([pid, grp]).agg(v=(val, "sum"), n=(val, "size")).reset_index()
    t = t[t.n >= min_n]
    t["s"] = t.v / (t.n + k) * 6
    g = t.groupby(pid).s
    mean, low, cnt = g.mean(), g.min(), g.size()
    if mode == "mean":
        return mean
    return pd.Series(np.where(cnt >= 2, 0.5 * mean + 0.5 * low, mean), index=mean.index)   # reward balance


def role_extras(role, b, pmr, pool):
    """Returns raw (value, sample size) for the five role-specific factors, aligned to pool."""
    idx = pool.index
    if role == "bat":
        r = b[b.striker_id.isin(idx) & b.nonwide]
        pid, val = "striker_id", "bat_val"
        n = r.groupby(pid).size()
        g = r.groupby(pid)
        sr = g.runs.sum() / n * 100
        bnd = g.is_bound.mean()
        dot = (r.runs == 0).groupby(r[pid]).mean()
        parts = [shrink(sr.reindex(idx), n.reindex(idx), 60), shrink(bnd.reindex(idx), n.reindex(idx), 60),
                 -shrink(dot.reindex(idx), n.reindex(idx), 60)]
        q = sum(zscore(p) for p in parts) / 3
        x = group_scores(r, pid, val, "pace_or_spin", 30, 12, "balance")
        y = group_scores(r, pid, val, "innings", 60, 12, "balance")
        ph = group_scores(r, pid, val, "phase", 18, 12, "mean")
    else:
        r = b[b.bowler_id.isin(idx) & b.legal]
        allb = b[b.bowler_id.isin(idx)]
        pid, val = "bowler_id", "bowl_val"
        n = r.groupby(pid).size()
        dot = (r.conc == 0).groupby(r[pid]).mean()
        bnd = r.groupby(pid).is_bound.mean()
        ext = (~allb.legal).groupby(allb[pid]).mean()
        parts = [shrink(dot.reindex(idx), n.reindex(idx), 60),               # more dot balls = better
                 -shrink(bnd.reindex(idx), n.reindex(idx), 60),              # fewer boundaries conceded = better
                 -shrink(ext.reindex(idx), n.reindex(idx), 60)]              # fewer wides / no-balls = better
        q = sum(zscore(p) for p in parts) / 3
        w24 = r.groupby(pid).bowl_wkt.sum() / n * 24
        x = shrink(w24.reindex(idx), n.reindex(idx), 60)
        y = group_scores(r, pid, val, "batting_type", 60, 12, "balance")
        ph = group_scores(r, pid, val, "phase", 18, 12, "mean")
    nb = r.groupby(pid).size().reindex(idx)
    big = pmr[pmr.big].groupby("player_id").v.agg(["mean", "size"]).reindex(idx)
    big = big[big["size"] >= 2]
    out = pd.DataFrame(index=idx)
    out["z_phase"] = zscore(shrink(ph.reindex(idx), nb, 60))
    out["z_q"] = zscore(q.reindex(idx))
    out["z_x"] = zscore(x.reindex(idx)) if role == "bowl" else zscore(shrink(x.reindex(idx), nb, 60))
    out["z_y"] = zscore(shrink(y.reindex(idx), nb, 60))
    bm = big["mean"].reindex(idx)
    out["z_big"] = zscore(shrink(bm, big["size"].reindex(idx).fillna(0), 3)) if bm.notna().any() else np.nan
    out["n_big"] = big["size"].reindex(idx).fillna(0).astype(int)
    return out


def score_role(role, b, pm, names, today, min_last_match, min_balls, recent_days):
    if role == "bat":
        pmr = pm[pm.batted].copy()
        pmr["v"] = pmr.bat_val + pmr.ns_pen
        pmr["va"] = pmr.bat_adj + pmr.ns_pen
        press = b[b.bat_press].groupby("striker_id").agg(pv=("bat_val", "sum"), pn=("nonwide", "sum"))
        pairs = b.groupby(["striker_id", "bowler_id"]).agg(v=("bat_val", "sum"), n=("nonwide", "sum")).reset_index()
        balls = b.groupby("striker_id").nonwide.sum()
    else:
        pmr = pm[pm.bowled].copy()
        pmr["v"] = pmr.bowl_val
        pmr["va"] = pmr.bowl_adj
        press = b[b.bowl_press].groupby("bowler_id").agg(pv=("bowl_val", "sum"), pn=("legal", "sum"))
        pairs = b.groupby(["bowler_id", "striker_id"]).agg(v=("bowl_val", "sum"), n=("legal", "sum")).reset_index()
        balls = b.groupby("bowler_id").legal.sum()

    rows = []
    for pid, x in pmr.sort_values(["player_id", "match_date", "match_id"]).groupby("player_id"):
        if recent_days:
            win = x[x.match_date >= today - pd.Timedelta(days=recent_days)]
            if win.empty:
                continue
            mu, sd = win.v.mean(), win.v.std(ddof=0)
        else:
            win = x.tail(10)
            w = 0.85 ** np.arange(len(win))[::-1]
            mu = np.average(win.v, weights=w)
            sd = np.sqrt(np.average((win.v - mu) ** 2, weights=w))
        rows.append(dict(
            player_id=pid, matches=len(x), n_recent=len(win), last_match=x.match_date.max(),
            matches_12m=(x.match_date >= today - pd.Timedelta(days=365)).sum(),
            f1=mu - 0.5 * sd, f4=x.va.mean(),
            f5=np.where(x.won, x.v, 0).mean() + 25 * x.mom.mean(), f6=x.v.mean()))
    P = pd.DataFrame(rows).set_index("player_id")

    press.columns = ["press_val", "press_balls"]
    P = P.join(press)
    P["f2"] = P.press_val / (P.press_balls + K_PRESS) * 6

    pairs.columns = ["player_id", "opp", "v", "n"]
    pairs = pairs[pairs.n >= 6].copy()
    pairs["per_over"] = pairs.v / (pairs.n + 12) * 6
    pairs["pos"] = (pairs.v > 0).astype(float)
    P = P.join(pairs.groupby("player_id").agg(n_opp=("opp", "nunique"), mean_pair=("per_over", "mean"),
                                               breadth=("pos", "mean")))
    P["balls"] = balls.reindex(P.index)
    P["player"] = names

    pool = P[(P.matches >= 15) & (P.matches_12m >= 5) & (P.last_match >= min_last_match)
             & (P.balls >= min_balls) & (P.n_opp >= 8)].copy()

    # ---- original six factors
    s1 = shrink(pool.f1, pool.n_recent, SHRINK_K["recent"])
    s4 = shrink(pool.f4, pool.matches, SHRINK_K["opp"])
    s5 = shrink(pool.f5, pool.matches, SHRINK_K["win"])
    s6 = shrink(pool.f6, pool.matches, SHRINK_K["hist"])
    vs = 0.5 * zscore(shrink(pool.mean_pair, pool.n_opp, SHRINK_K["vs"])) \
        + 0.5 * zscore(shrink(pool.breadth, pool.n_opp, SHRINK_K["vs"]))
    pool["z_recent"], pool["z_pressure"], pool["z_vs_all"] = zscore(s1), zscore(pool.f2), zscore(vs)
    pool["z_opp"], pool["z_win"], pool["z_hist"] = zscore(s4), zscore(s5), zscore(s6)

    # ---- new role-specific factors
    pool = pool.join(role_extras(role, b, pmr, pool))

    wts = {k: v * BASE_SHARE for k, v in BASE.items()}
    for z_col, (_, wgt) in ROLE_FACTORS[role].items():
        wts[z_col] = wgt
    w = pd.Series(wts)
    Z = pool[list(w.index)]
    pool["composite"] = (Z.fillna(0) * w).sum(axis=1) / (Z.notna() * w).sum(axis=1)   # missing factor: reweight, never 0
    pool["overall_rating"] = (50 + 20 * pool.composite).clip(0, 100).round(1)          # 50 = pool average
    names_map = {"z_recent": "recent_consistency", "z_pressure": "pressure_collapse", "z_vs_all": "vs_all_participants",
                 "z_opp": "opposition_strength", "z_win": "match_winning", "z_hist": "historical"}
    names_map.update({k: v[0] for k, v in ROLE_FACTORS[role].items()})
    for z_col, name in names_map.items():
        pool[name] = (50 + 20 * pool[z_col]).clip(0, 100).round(1)
    pool = pool.sort_values("composite", ascending=False)
    pool["rank"] = range(1, len(pool) + 1)
    pool["last_match"] = pool.last_match.dt.strftime("%Y-%m-%d")
    return pool, list(names_map.values())


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Top 10 batters and bowlers from ball-by-ball data")
    ap.add_argument("--ball-dir", required=True)
    ap.add_argument("--matches", required=True)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--today", default=None, help="reference date (default: latest match date in data)")
    ap.add_argument("--min-last-match", default="2026-03-01",
                    help="player must have played on/after this date (default 2026-03-01)")
    ap.add_argument("--min-balls", type=int, default=250, help="min balls faced / bowled")
    ap.add_argument("--recent-days", type=int, default=0,
                    help="0 = last 10 matches (default); e.g. 365 = all matches in the last year")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--no-open-dashboard", action="store_true",
                    help="generate the dashboard without opening it in a browser")
    a = ap.parse_args()

    matches = pd.read_csv(a.matches, parse_dates=["match_date"])
    matches["big"] = matches.knock_out.fillna(0).astype(int) == 1          # finals, semis, qualifiers, eliminators
    today = pd.Timestamp(a.today) if a.today else matches.match_date.max()

    b = prepare_balls(load_balls(a.ball_dir), matches)
    print(f"Analysing {len(b):,} balls (innings 1-2) across {b.match_id.nunique()} matches")
    b = add_prior_form(b, matches)
    pm = player_match_table(b, matches)
    names = pd.concat([
        b[["striker_id", "striker_name"]].set_axis(["player_id", "n"], axis=1),
        b[["bowler_id", "bowler_name"]].set_axis(["player_id", "n"], axis=1),
    ]).drop_duplicates("player_id").set_index("player_id").n

    os.makedirs(a.out_dir, exist_ok=True)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 40)
    for role, label in (("bat", "batters"), ("bowl", "bowlers")):
        pool, factor_cols = score_role(role, b, pm, names, today, pd.Timestamp(a.min_last_match),
                                       a.min_balls, a.recent_days)
        cols = ["rank", "player"] + factor_cols + ["overall_rating", "matches", "balls", "n_big", "last_match"]
        pool[cols].round(3).to_csv(os.path.join(a.out_dir, f"ranking_{label}.csv"), index=False)

    dashboard_path = build_dashboard(a.out_dir, a.top)
    print(f"Dashboard saved to {dashboard_path}")
    if not a.no_open_dashboard:
        if webbrowser.open(Path(dashboard_path).as_uri()):
            print("Opened the rankings dashboard in your browser.")
        else:
            print("Could not open a browser automatically; open the dashboard file above.")


if __name__ == "__main__":
    main()
