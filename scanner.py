import sys
import os
import time
import random
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel

# Add the build directory to the Python path to find fast_pricer.pyd
build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'build'))
sys.path.append(build_dir)
import fast_pricer

class MockMarketDataStream:
    def __init__(self, current_spot):
        self.spot = current_spot
        # 51 strikes total
        self.strikes = [self.spot - 25 + i for i in range(51)]
    
    def fetch_chain(self):
        # Walk the spot price slightly
        self.spot += random.uniform(-0.5, 0.5)
        chain = []
        for K in self.strikes:
            base_value = max(self.spot - K, 0) + random.uniform(0.1, 5.0)
            bid = max(0.01, base_value - random.uniform(0.1, 0.5))
            ask = bid + random.uniform(0.05, 0.3)
            
            # 5% chance of an irrational market Ask (Arbitrage opportunity)
            if random.random() < 0.05:
                ask = max(0.01, base_value - random.uniform(1.0, 2.0))
                
            chain.append({
                'strike': K,
                'bid': bid,
                'ask': ask
            })
        return self.spot, chain

def run_scanner():
    pricer = fast_pricer.HestonMonteCarloPricer()
    params = fast_pricer.HestonParams()
    params.V0 = 0.04
    params.r = 0.05
    params.kappa = 2.0
    params.theta = 0.04
    params.sigma = 0.1
    params.rho = -0.5
    T = 1.0
    
    # 10,000 paths per contract
    num_paths = 10000
    num_steps = 100

    stream = MockMarketDataStream(100.0)
    console = Console()
    
    with Live(console=console, refresh_per_second=4, screen=True) as live:
        try:
            while True:
                start_time = time.perf_counter()
                
                spot, chain = stream.fetch_chain()
                params.S0 = spot
                
                table = Table(title=f"SIMD Options Arbitrage Scanner | Underlying Spot: ${spot:.2f}", expand=True)
                table.add_column("Strike", justify="right", style="cyan")
                table.add_column("Market Bid", justify="right")
                table.add_column("Market Ask", justify="right")
                table.add_column("C++ Fair Value (AVX2)", justify="right", style="magenta")
                table.add_column("Status", justify="center")

                arb_count = 0
                
                # Sort chain by distance to spot to display only the closest 15 contracts
                display_chain = sorted(chain, key=lambda x: abs(x['strike'] - spot))[:15]
                display_chain.sort(key=lambda x: x['strike'])
                
                for option in chain:
                    K = option['strike']
                    
                    # The Hot Path: Microsecond C++ AVX2 Pricing
                    theo_price = pricer.price_call_avx2(params, K, T, num_paths, num_steps)
                    
                    market_ask = option['ask']
                    market_bid = option['bid']
                    
                    is_arb = market_ask < theo_price - 0.1
                    if is_arb:
                        arb_count += 1
                        
                    if option in display_chain:
                        if is_arb:
                            status = "[bold green]BUY ARBITRAGE[/bold green]"
                            row_style = "bold green"
                        else:
                            status = "Hold"
                            row_style = ""
                        
                        table.add_row(
                            f"{K:.2f}",
                            f"${market_bid:.2f}",
                            f"${market_ask:.2f}",
                            f"${theo_price:.2f}",
                            status,
                            style=row_style
                        )
                
                elapsed_us = (time.perf_counter() - start_time) * 1_000_000
                
                summary = Table.grid()
                summary.add_column()
                summary.add_row(f"[bold yellow]Performance:[/bold yellow] Priced {len(chain)} contracts ({(len(chain)*num_paths):,} paths) in {elapsed_us:.1f} microseconds.")
                summary.add_row(f"[bold green]Arbitrage Opportunities Found:[/bold green] {arb_count}")
                summary.add_row("[dim]Press Ctrl+C to exit[/dim]")
                
                layout = Layout()
                layout.split_column(
                    Layout(Panel(table, border_style="blue"), ratio=1),
                    Layout(Panel(summary, title="Metrics", border_style="green"), size=5)
                )
                
                live.update(layout)
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run_scanner()
