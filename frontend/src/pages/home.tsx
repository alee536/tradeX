import { useState, useEffect, useMemo } from "react";
import { Link } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { usePublicCoinSettings } from "@/hooks/use-public-coin-settings";
import { SocialLinks } from "@/components/ui/social-links";
import {
  formatCoinRate,
  formatTotalSupply,
  landingProfitPercent,
  planReturnAmount,
} from "@/lib/home-public-settings";

const HOME_FEATURES = [
  { icon: "⚡", title: "INSTANT EXECUTION", desc: "Trades execute in milliseconds. Our matching engine handles 100,000+ transactions per second." },
  { icon: "🔒", title: "MILITARY SECURITY", desc: "256-bit encryption, 2FA, and cold-wallet storage keep your assets safe." },
  { icon: "💎", title: "REFERRAL REWARDS", desc: "Earn passive income by inviting friends. Our sponsor system rewards every layer." },
  { icon: "🌐", title: "GLOBAL ACCESS", desc: "Trade from anywhere in the world, 24/7. Multiple fiat on-ramps." },
  { icon: "📊", title: "LIVE ANALYTICS", desc: "Real-time charts, portfolio tracking, and market depth analysis." },
];

const INVESTMENT_PLANS = [
  { amount: 10, label: "Minimum Invest" },
  { amount: 50, label: "Starter Pack" },
  { amount: 100, label: "Growth Pack", featured: true },
  { amount: 500, label: "Pro Pack" },
  { amount: 1000, label: "Elite Pack" },
];

export default function Home() {
  const { user } = useAuth();
  const [investment, setInvestment] = useState(100);

  const { data: publicSettings } = usePublicCoinSettings();

  const currencySymbol = publicSettings?.currency_symbol || "USD";
  const coinRateDisplay = formatCoinRate(publicSettings?.coin_rate, currencySymbol);
  const totalSupplyDisplay = formatTotalSupply(publicSettings?.total_coin_supply);
  const profitPercent = landingProfitPercent(publicSettings?.profit_percentage);

  const { profit, total } = useMemo(
    () => planReturnAmount(investment, profitPercent),
    [investment, profitPercent],
  );

  const planCards = useMemo(
    () =>
      INVESTMENT_PLANS.map((plan) => {
        const { profit: planProfit, total: planTotal } = planReturnAmount(
          plan.amount,
          profitPercent,
        );
        return {
          ...plan,
          amountLabel: `$${plan.amount.toLocaleString()}`,
          returnLabel: `$${planTotal.toLocaleString()}`,
          profitLabel: planProfit,
        };
      }),
    [profitPercent],
  );

  useEffect(() => {
    if (user) {
      document.body.classList.add("logged-in");
    } else {
      document.body.classList.remove("logged-in");
    }
    return () => document.body.classList.remove("logged-in");
  }, [user]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950">
      <style>{`
        :root {
          --bg-primary:    #0a0e1a;
          --bg-secondary:  #0d1225;
          --bg-card:       #111827;
          --bg-card-hover: #141d2e;
          --accent-blue:   #2d7fff;
          --accent-cyan:   #00d4ff;
          --accent-green:  #00f5a0;
          --accent-purple: #7c4dff;
          --text-primary:  #e8f0fe;
          --text-secondary:#8899bb;
          --text-muted:    #4a5878;
          --border:        rgba(45,127,255,0.15);
          --border-bright: rgba(45,127,255,0.4);
        }
      `}</style>

      {/* TICKER BAR */}
      <div className="border-b border-cyan-500/20 bg-slate-900/50 backdrop-blur overflow-hidden">
        <div className="animate-scroll flex gap-0">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="flex gap-0 flex-shrink-0">
              <div className="flex items-center gap-2 px-9 py-2.5 text-xs font-mono text-slate-400 border-r border-slate-700 whitespace-nowrap">
                <span className="text-cyan-400 font-semibold">BTC/USD</span>
                <span className="text-cyan-300">$67,420.50</span>
                <span className="text-green-400">+2.34%</span>
              </div>
              <div className="flex items-center gap-2 px-9 py-2.5 text-xs font-mono text-slate-400 border-r border-slate-700 whitespace-nowrap">
                <span className="text-cyan-400 font-semibold">ETH/USD</span>
                <span className="text-cyan-300">$3,812.00</span>
                <span className="text-green-400">+1.87%</span>
              </div>
              <div className="flex items-center gap-2 px-9 py-2.5 text-xs font-mono text-slate-400 border-r border-slate-700 whitespace-nowrap">
                <span className="text-cyan-400 font-semibold">24TX/{currencySymbol}</span>
                <span className="text-cyan-300">{coinRateDisplay}</span>
                <span className="text-green-400">Live rate</span>
              </div>
              <div className="flex items-center gap-2 px-9 py-2.5 text-xs font-mono text-slate-400 whitespace-nowrap">
                <span className="text-cyan-400 font-semibold">SOL/USD</span>
                <span className="text-cyan-300">$172.40</span>
                <span className="text-green-400">+3.10%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* HERO SECTION */}
      <section className="relative min-h-[85vh] flex items-center px-6 md:px-16 lg:px-20 py-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent pointer-events-none" />
        <div className="absolute top-20 right-10 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-blue-900/30 border border-blue-500/40 rounded-full px-4 py-2 mb-8">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-xs font-mono font-semibold text-cyan-400 tracking-wider">LIVE TRADING — 24TX</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-black leading-tight mb-6">
            Trade Smarter.<br />
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-green-400 bg-clip-text text-transparent">
              Earn Faster.
            </span>
            <br />
            Live Bolder.
          </h1>

          {/* Subheading */}
          <p className="text-lg md:text-xl text-slate-300 mb-8 max-w-2xl leading-relaxed">
            TRADEX is the next-generation cryptocurrency exchange platform built for serious traders. Buy, sell, and earn with zero compromise on speed, security, or yield.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap gap-4 items-center">
            {user ? (
              <>
                <Link href="/user/dashboard">
                  <a className="px-8 py-3 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all">
                    GO TO DASHBOARD
                  </a>
                </Link>
                <Link href="/purchase">
                  <a className="px-8 py-3 border border-cyan-500/40 text-cyan-400 font-bold rounded-lg hover:bg-cyan-500/10 transition-all">
                    BUY COINS
                  </a>
                </Link>
              </>
            ) : (
              <>
                <Link href="/register">
                  <a className="px-8 py-3 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all">
                    START TRADING
                  </a>
                </Link>
                <Link href="/login">
                  <a className="px-8 py-3 border border-cyan-500/40 text-cyan-400 font-bold rounded-lg hover:bg-cyan-500/10 transition-all">
                    LOGIN
                  </a>
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Stats Cards - Right Side */}
        <div className="hidden lg:flex absolute right-16 top-1/2 -translate-y-1/2 flex-col gap-4 w-80">
          <div className="bg-slate-800/50 border border-blue-500/20 rounded-xl p-5 backdrop-blur hover:border-blue-500/40 transition-all">
            <p className="text-xs font-mono text-slate-500 mb-2 uppercase tracking-widest">Coin Rate</p>
            <p className="text-2xl font-black text-cyan-400">{coinRateDisplay}</p>
            <p className="text-sm text-green-400 mt-1">Admin rate · live</p>
          </div>
          <div className="bg-slate-800/50 border border-blue-500/20 rounded-xl p-5 backdrop-blur hover:border-blue-500/40 transition-all">
            <p className="text-xs font-mono text-slate-500 mb-2 uppercase tracking-widest">Total Supply</p>
            <p className="text-2xl font-black text-cyan-400">{totalSupplyDisplay}</p>
            <p className="text-sm text-slate-400 mt-1">24TX tokens</p>
          </div>
          <div className="bg-slate-800/50 border border-blue-500/20 rounded-xl p-5 backdrop-blur hover:border-blue-500/40 transition-all">
            <p className="text-xs font-mono text-slate-500 mb-2 uppercase tracking-widest">Active Users</p>
            <p className="text-2xl font-black text-cyan-400">4 / 11</p>
            <p className="text-sm text-green-400 mt-1">↑ Growing fast</p>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="px-6 md:px-16 lg:px-20 py-24 border-y border-blue-500/20">
        <div className="text-center mb-16">
          <p className="text-xs font-mono font-bold text-blue-400 tracking-widest mb-4">// WHY TRADEX</p>
          <h2 className="text-4xl md:text-5xl font-black">
            Built for the <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Future of Finance</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {HOME_FEATURES.map((f, i) => (
            <div
              key={i}
              className="bg-slate-800/30 border border-blue-500/20 rounded-2xl p-8 backdrop-blur hover:border-blue-500/40 hover:bg-slate-800/50 transition-all group"
            >
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="font-bold text-lg text-white mb-3">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* INVESTMENT PLANS & CALCULATOR */}
      <section className="relative px-6 md:px-16 lg:px-20 py-24 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-green-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="text-center mb-16 relative z-10">
          <p className="text-xs font-mono font-bold text-blue-400 tracking-widest mb-4">// EARN WITH TRADEX</p>
          <h2 className="text-4xl md:text-5xl font-black mb-4">
            Invest &amp; Get{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-green-400 bg-clip-text text-transparent">
              {profitPercent}% after 120 hours
            </span>
          </h2>
          <p className="text-slate-300 max-w-2xl mx-auto">
            Start with as little as <span className="text-cyan-400 font-bold">$10</span>. Every dollar you
            invest returns {100 + profitPercent}% after <span className="text-cyan-400 font-bold">120 hours</span> — admin-configured yield.
          </p>
        </div>

        {/* Plan Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-12 relative z-10">
          {planCards.map((plan, i) => (
            <div
              key={i}
              className={`rounded-2xl p-6 backdrop-blur transition-all ${
                plan.featured
                  ? "bg-gradient-to-br from-green-900/40 to-slate-900/40 border border-green-500/40 shadow-lg shadow-green-500/20"
                  : "bg-slate-800/30 border border-blue-500/20 hover:border-blue-500/40 hover:bg-slate-800/50"
              }`}
            >
              {plan.featured && (
                <div className="inline-block bg-green-900/50 text-green-400 text-xs font-bold px-3 py-1 rounded-full mb-4">
                  🔥 Most Popular
                </div>
              )}
              <div className="text-3xl font-black text-cyan-400 mb-2">{plan.amountLabel}</div>
              <p className="text-xs font-mono text-slate-500 mb-4 uppercase tracking-widest">{plan.label}</p>
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 mb-3">
                <p className="text-xs text-slate-400 mb-1">You Get Back</p>
                <p className="text-lg font-black text-green-400">{plan.returnLabel}</p>
              </div>
              <p className="text-xs text-slate-500">
                After <span className="text-cyan-400 font-bold">120 hours</span> · {plan.profitLabel} profit
              </p>
            </div>
          ))}
        </div>

        {/* Calculator */}
        <div className="max-w-2xl mx-auto relative z-10">
          <div className="bg-slate-800/50 border border-blue-500/40 rounded-2xl p-8 backdrop-blur">
            <div className="mb-2">
              <h3 className="font-bold text-lg text-white">💰 Returns Calculator</h3>
              <p className="text-xs text-slate-400 font-mono">Drag the slider to see your returns after 120 hours</p>
            </div>

            <div className="mt-6 mb-6">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">Investment Amount</label>
              <div className="flex items-center gap-3">
                <span className="text-lg font-bold text-cyan-400">$</span>
                <input
                  type="range"
                  min="10"
                  max="10000"
                  step="10"
                  value={investment}
                  onChange={(e) => setInvestment(parseInt(e.target.value))}
                  className="flex-1 h-2 bg-gradient-to-r from-blue-500/50 to-slate-700 rounded-full appearance-none cursor-pointer accent-cyan-500"
                />
                <span className="text-lg font-black text-cyan-400 min-w-fit">${investment.toLocaleString()}</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 bg-green-500/5 border border-green-500/20 rounded-xl p-4">
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-2 uppercase tracking-widest">You Invest</p>
                <p className="text-xl font-black text-cyan-400">${investment.toLocaleString()}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-2 uppercase tracking-widest">120 Hours Profit</p>
                <p className="text-xl font-black text-green-400">+${profit.toLocaleString()}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-2 uppercase tracking-widest">Total Return</p>
                <p className="text-xl font-black text-white">${total.toLocaleString()}</p>
              </div>
            </div>

            <p className="text-xs text-slate-500 text-center mt-4 font-mono">
              Fixed <span className="text-cyan-400">{profitPercent}% yield</span> · Minimum <span className="text-cyan-400">$10</span> · Returns paid after <span className="text-cyan-400">120 hours</span>
            </p>
          </div>
        </div>
      </section>

      {/* MARKET TABLE */}
      <section className="px-6 md:px-16 lg:px-20 py-24 border-y border-blue-500/20">
        <div className="text-center mb-12">
          <p className="text-xs font-mono font-bold text-blue-400 tracking-widest mb-4">// LIVE MARKETS</p>
          <h2 className="text-4xl md:text-5xl font-black">
            Top <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Cryptocurrencies</span>
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-blue-500/20">
                <th className="text-left py-4 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">#</th>
                <th className="text-left py-4 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Asset</th>
                <th className="text-right py-4 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Price</th>
                <th className="text-right py-4 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">24h Change</th>
                <th className="text-right py-4 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Market Cap</th>
              </tr>
            </thead>
            <tbody>
              {[
                { rank: 1, name: "Bitcoin", symbol: "BTC", price: "$67,420.50", change: "+2.34%", cap: "$1.32T", icon: "₿", color: "from-orange-500 to-yellow-500" },
                { rank: 2, name: "Ethereum", symbol: "ETH", price: "$3,812.00", change: "+1.87%", cap: "$458B", icon: "Ξ", color: "from-purple-500 to-blue-500" },
                { rank: 3, name: "TRADEX", symbol: "24TX", price: coinRateDisplay, change: "Live", cap: "—", icon: "T", color: "from-blue-500 to-cyan-500" },
              ].map((coin, i) => (
                <tr key={i} className="border-b border-blue-500/10 hover:bg-blue-500/5 transition-colors">
                  <td className="py-4 px-4 text-slate-400">{coin.rank}</td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${coin.color} flex items-center justify-center text-white text-xs font-bold`}>
                        {coin.icon}
                      </div>
                      <div>
                        <p className="font-bold text-white">{coin.name}</p>
                        <p className="text-xs text-slate-500">{coin.symbol}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right text-cyan-400 font-mono">{coin.price}</td>
                  <td className="py-4 px-4 text-right text-green-400 font-mono">{coin.change}</td>
                  <td className="py-4 px-4 text-right text-slate-400 font-mono">{coin.cap}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* CTA SECTION */}
      <section className="relative px-6 md:px-16 lg:px-20 py-24 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent pointer-events-none" />
        <div className="relative z-10">
          <h2 className="text-5xl md:text-6xl font-black mb-4">
            Ready to <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Join TRADEX?</span>
          </h2>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Buy 24TX at the live admin rate ({coinRateDisplay}) — lock in your position today.
          </p>
          {user ? (
            <Link href="/purchase">
              <a className="inline-block px-10 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all text-lg">
                BUY 24TX NOW
              </a>
            </Link>
          ) : (
            <Link href="/register">
              <a className="inline-block px-10 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all text-lg">
                CREATE FREE ACCOUNT
              </a>
            </Link>
          )}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-blue-500/20 bg-slate-900/50 px-6 md:px-16 lg:px-20 py-12">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-xl font-black text-cyan-400 tracking-widest">TRADEX</div>
          <p className="text-sm text-slate-400 font-mono">© 2025 TRADEX. All rights reserved. Trade responsibly.</p>
          <div className="flex items-center gap-4">
            <SocialLinks />
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-scroll {
          animation: scroll 40s linear infinite;
        }
      `}</style>
    </div>
  );
}
