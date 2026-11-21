from django.utils import timezone
from .models import PortfolioHistory
from .models import Holding
import yfinance as yf

def fetch_prices(symbols):
    return yf.download(symbols, period="1d", interval="1d")["Close"].iloc[-1]

def fetch_stock_history(symbol):
    return yf.Ticker(symbol).history(period="1mo")["Close"].dropna()