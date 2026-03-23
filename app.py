import streamlit as st
import pandas as pd
from datetime import date
import io
import requests

st.set_page_config(
    page_title="Portfolio Calculator",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0a0e27;
    }
    .stButton>button {
        background-color: #00ffcc;
        color: #0a0e27;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #00d9b3;
        box-shadow: 0 4px 12px rgba(0, 255, 204, 0.4);
    }
    h1 {
        color: #00ffcc;
        font-family: 'Arial', sans-serif;
        letter-spacing: -1px;
    }
    h2, h3 {
        color: #00ffcc;
    }
    .success-box {
        padding: 1rem;
        background-color: rgba(0, 255, 136, 0.1);
        border-left: 4px solid #00ff88;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: rgba(255, 51, 102, 0.1);
        border-left: 4px solid #ff3366;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'holdings' not in st.session_state:
    st.session_state.holdings = []

# Exchange mapping
EXCHANGE_MAP = {
    'NASDAQ': {'mic': 'XNAS', 'country': 'US'},
    'NYSE': {'mic': 'XNYS', 'country': 'US'},
    'TSX': {'mic': 'XTSE', 'country': 'CA'},
    'LSE': {'mic': 'XLON', 'country': 'GB'},
    'TSE': {'mic': 'XTKS', 'country': 'JP'},
    'ASX': {'mic': 'XASX', 'country': 'AU'},
    'Euronext': {'mic': 'XAMS', 'country': 'NL'},
}

def fetch_stock_price(ticker):
    """Fetch current stock price using Yahoo Finance API"""
    try:
        # Using Yahoo Finance query API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                
                # Try to get the regular market price
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    price = result['meta']['regularMarketPrice']
                    return float(price)
                
                # Fallback to previous close
                if 'meta' in result and 'previousClose' in result['meta']:
                    price = result['meta']['previousClose']
                    return float(price)
        
        return None
        
    except Exception as e:
        st.warning(f"⚠️ Error fetching {ticker}: {str(e)}")
        return None

def detect_exchange_from_ticker(ticker):
    """Auto-detect exchange based on ticker suffix or common patterns"""
    ticker_upper = ticker.upper()
    
    # Canadian stocks (TSX)
    if ticker_upper.endswith('.TO') or ticker_upper.endswith('.V'):
        return 'TSX'
    
    # UK stocks (LSE)
    if ticker_upper.endswith('.L'):
        return 'LSE'
    
    # Japanese stocks (TSE)
    if ticker_upper.endswith('.T'):
        return 'TSE'
    
    # Australian stocks (ASX)
    if ticker_upper.endswith('.AX'):
        return 'ASX'
    
    # European stocks
    if ticker_upper.endswith('.AS') or ticker_upper.endswith('.PA'):
        return 'Euronext'
    
    # Default to NASDAQ for US stocks without suffix
    # You can also check if it's a known NYSE stock
    nyse_indicators = ['^', 'BRK.', 'BRK-']
    for indicator in nyse_indicators:
        if indicator in ticker_upper:
            return 'NYSE'
    
    return 'NASDAQ'

# Header
st.title("📊 PORTFOLIO CALCULATOR")
st.markdown("**Auto-fetch prices • Equal weighting • Export ready**")

# Settings Section
st.header("⚙️ Portfolio Settings")
col1, col2 = st.columns(2)

with col1:
    portfolio_value = st.number_input(
        "Total Portfolio Value ($)",
        min_value=0,
        value=1000000,
        step=10000,
        format="%d"
    )

with col2:
    transaction_date = st.date_input(
        "Transaction Date",
        value=date.today()
    )

st.divider()

# Holdings Input Section
st.header("📈 Add Holdings")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    new_ticker = st.text_input("Stock Ticker", placeholder="e.g., AAPL, MSFT, SHOP.TO", key="new_ticker").upper()

with col2:
    # Auto-detect exchange based on ticker
    auto_exchange = detect_exchange_from_ticker(new_ticker) if new_ticker else 'NASDAQ'
    
    new_exchange = st.selectbox(
        "Exchange (Auto-detected)",
        options=list(EXCHANGE_MAP.keys()),
        index=list(EXCHANGE_MAP.keys()).index(auto_exchange),
        key="new_exchange",
        help="Exchange is automatically detected from ticker suffix. You can change it if needed."
    )

with col3:
    st.write("")  # Spacing
    st.write("")  # Spacing
    if st.button("➕ Add Stock", use_container_width=True):
        if new_ticker:
            with st.spinner(f'Fetching price for {new_ticker}...'):
                price = fetch_stock_price(new_ticker)
                
                if price:
                    st.session_state.holdings.append({
                        'ticker': new_ticker,
                        'exchange': new_exchange,
                        'country': EXCHANGE_MAP[new_exchange]['country'],
                        'mic': EXCHANGE_MAP[new_exchange]['mic'],
                        'price': price
                    })
                    st.success(f"✅ Added {new_ticker} at ${price:.2f}")
                    st.rerun()
                else:
                    st.error(f"❌ Unable to fetch price for {new_ticker}. Please check the ticker symbol.")
        else:
            st.warning("⚠️ Please enter a ticker symbol")

st.divider()

# Display Current Holdings
if st.session_state.holdings:
    st.header("📋 Current Holdings")
    
    # Calculate equal weighting
    num_holdings = len(st.session_state.holdings)
    value_per_holding = portfolio_value / num_holdings if num_holdings > 0 else 0
    
    # Create dataframe for display
    holdings_data = []
    total_shares = 0
    
    for i, holding in enumerate(st.session_state.holdings):
        shares = int(value_per_holding / holding['price']) if holding['price'] > 0 else 0
        total_value = shares * holding['price']
        total_shares += shares
        
        holdings_data.append({
            'Ticker': holding['ticker'],
            'Exchange': holding['exchange'],
            'Country': holding['country'],
            'Current Price': f"${holding['price']:.2f}",
            'Shares': f"{shares:,}",
            'Total Value': f"${total_value:,.2f}"
        })
    
    # Display table
    df_display = pd.DataFrame(holdings_data)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Summary metrics
    st.subheader("📊 Portfolio Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Holdings", num_holdings)
    
    with col2:
        st.metric("Value per Holding", f"${value_per_holding:,.0f}")
    
    with col3:
        st.metric("Total Shares", f"{total_shares:,}")
    
    st.divider()
    
    # Action Buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Refresh All Prices", use_container_width=True):
            with st.spinner('Refreshing prices...'):
                updated = 0
                for holding in st.session_state.holdings:
                    new_price = fetch_stock_price(holding['ticker'])
                    if new_price:
                        holding['price'] = new_price
                        updated += 1
                st.success(f"✅ Refreshed {updated}/{len(st.session_state.holdings)} prices!")
                st.rerun()
    
    with col2:
        # Generate CSV for download
        csv_data = []
        for holding in st.session_state.holdings:
            shares = int(value_per_holding / holding['price']) if holding['price'] > 0 else 0
            csv_data.append({
                'Ticker': holding['ticker'],
                'Listing Country': holding['country'],
                'Shares': shares,
                'Cost Basis': f"{holding['price']:.2f}"
            })
        
        df_export = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Import CSV",
            data=csv_string,
            file_name=f"portfolio_import_{transaction_date.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col3:
        if st.button("🗑️ Clear All Holdings", use_container_width=True):
            st.session_state.holdings = []
            st.rerun()
    
    # Individual delete buttons
    st.subheader("✏️ Manage Holdings")
    for i, holding in enumerate(st.session_state.holdings):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"**{holding['ticker']}** - {holding['exchange']} - ${holding['price']:.2f}")
        with col2:
            if st.button("❌", key=f"delete_{i}"):
                st.session_state.holdings.pop(i)
                st.rerun()

else:
    st.info("👆 Add your first stock above to get started!")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #8892b0; padding: 1rem;'>
    <small>💡 Tip: Make sure tickers are entered correctly (e.g., AAPL for Apple, MSFT for Microsoft)</small><br>
    <small>📍 For Canadian stocks on TSX, use .TO suffix (e.g., SHOP.TO)</small>
</div>
""", unsafe_allow_html=True)
