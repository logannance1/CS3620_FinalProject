import csv
from decimal import Decimal
import json
from django.http import Http404, HttpResponseBadRequest, HttpResponse
import pdfkit
import yfinance as yf
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.core.paginator import Paginator
from django.template import loader
from core import models
from core import services

# Create your views here.
@login_required
def dashboard(request):
    return render(request, "core/loading.html", {
        "title": "Dashboard",
        "refresh": "api/dashboard-refresh/"
    })

@login_required
def dashboard_refresh(request):
    today = timezone.localdate()
    holdings = models.Holding.objects.filter(user=request.user)
    user_cash, _ = models.UserCash.objects.get_or_create(user=request.user)
    cash = float(user_cash.cash)
    portfolio_value = cash
    symbols = [holding.symbol for holding in holdings]
    key = f"user_{request.user.id}_holdings"
    prices = cache.get_or_set(key, lambda: services.fetch_prices(symbols), 300)

    for holding in holdings:
        holding.current_price = prices[holding.symbol]
        holding.value = holding.current_price * holding.shares
        portfolio_value += holding.value

    for holding in holdings:
        holding.allocation = f"{holding.value / portfolio_value * 100:.2f}%"
        holding.current_price = f"${holding.current_price:,.2f}"
        holding.value = f"${holding.value:,.2f}"

    models.PortfolioHistory.objects.update_or_create(
        user=request.user,
        date=today,

        defaults={
            'value': portfolio_value,
        }
    )

    portfolio_value = f"${portfolio_value:,.2f}"

    history = reversed(
        list(models.PortfolioHistory.objects.filter(user=request.user) \
        .order_by('-date')[:50])
    )

    labels = []
    data = []

    for h in history:
        labels.append(h.date.strftime("%b %d, %Y"))
        data.append(float(h.value))
    
    return render(request, 'core/partial/dashboard-refresh.html', {
        "portfolio_value": portfolio_value,
        "holdings": holdings,
        "labels": json.dumps(labels),
        'data': json.dumps(data),
    })

@login_required
def stocks(request):
    stock_name = request.GET.get("stock_name")
    page = request.GET.get("page")
    url = "/api/stocks-refresh/"

    if stock_name:
        url += f"?stock_name={stock_name}"

        if page:
            url += f"&page={page}"
    elif page:
        url += f"?page={page}"
        
    return render(request, "core/loading.html", {
        "title": "Stocks",
        "refresh": url
    })

@login_required
def stocks_refresh(request):
    stock_list = models.Stock.objects.all()
    symbols = [stock.symbol for stock in stock_list]

    prices = cache.get_or_set(
        "stock_prices",
        lambda: services.fetch_prices(symbols),
        300
    )

    stock_name = request.GET.get("stock_name")

    if stock_name:
        stock_list = stock_list.filter(symbol__icontains=stock_name)

    paginator = Paginator(stock_list, 4)
    page = request.GET.get("page")
    stock_list = paginator.get_page(page)

    for stock in stock_list:
        stock.price = prices[stock.symbol]

    return render(request, 'core/partial/stocks-refresh.html', {
        "stock_list": stock_list,
        "stock_name": stock_name,
    })

@login_required
def stock_details(request, symbol):
    symbol = symbol.upper()
    form_error = ""

    if request.method == "POST":
        stock = models.Stock.objects.get(symbol=symbol)
        trade_type = request.POST.get("trade_type")
        shares = int(request.POST.get("share-amount"))
        price = Decimal(request.POST.get("price"))
        total = shares * price
        trade = models.Trade(user=request.user,
            stock=stock, shares=shares, price=price)

        if trade_type == "buy":
            trade.trade_type = models.Trade.TradeType.BUY
            user_cash = models.UserCash.objects.get(user=request.user)

            if user_cash.cash >= total:
                user_cash.cash -= total

                holding, created = models.Holding.objects.get_or_create(
                    user=request.user,
                    symbol=symbol,
                    defaults={ "shares": shares }
                )

                if not created:
                    holding.shares += shares
                    holding.save()
                
                user_cash.save()
                trade.save()
                return redirect("confirmation", pk=trade.pk)
            else:
                form_error = "Buy trade cannot exceed buying power!"
        elif trade_type == "sell":
            trade.trade_type = models.Trade.TradeType.SELL
            holding = models.Holding.objects.filter(user=request.user,
                symbol=symbol).first()

            if holding:
                if holding.shares < shares:
                    form_error = "Sell trade cannot exceed shares owned!"
                else:
                    if holding.shares == shares:
                        holding.delete()
                    else:
                        holding.shares -= shares
                        holding.save()

                    user_cash = models.UserCash.objects.get(user=request.user)
                    user_cash.cash += total
                    user_cash.save()
                    trade.save()
                    return redirect("confirmation", pk=trade.pk)
            else:
                form_error = "Sell trade cannot exceed shares owned!"
        else:
            return HttpResponseBadRequest("Invalid trade type")
        
    return render(request, 'core/loading.html', {
        "title": symbol,
        'refresh': f"/api/stock-details-refresh/{symbol}/?form_error={form_error}",
    })

@login_required
def stock_details_refresh(request, symbol):
    stock = get_object_or_404(models.Stock, symbol=symbol)
    history = services.fetch_stock_history(stock.symbol)
    labels = history.index.strftime("%b %d, %Y").tolist()
    data = history.astype(float).tolist()
    cash = models.UserCash.objects.get(user=request.user).cash
    form_error = request.GET.get("form_error")
    holding = models.Holding.objects \
        .filter(user=request.user, symbol=stock.symbol).first()

    shares = 0 if not holding else holding.shares
    current_price = data[-1]

    return render(request, "core/partial/stock-details-refresh.html", {
        "current_price": current_price,
        "buying_power": cash,
        "shares_owned": shares,
        "desc": stock.desc,
        "form_error": form_error,
        "labels": json.dumps(labels),
        "data": json.dumps(data),
    })

@login_required
def confirmation(request, pk):
    trade = get_object_or_404(models.Trade, pk=pk, user=request.user)
    trade.total = trade.shares * trade.price
    return render(request, "core/confirmation.html", { "trade": trade })

@login_required
def history(request):
    trades = models.Trade.objects.filter(user=request.user)
    paginator = Paginator(trades, 10)
    page = request.GET.get("page")
    trades = paginator.get_page(page)

    for trade in trades:
        trade.total = trade.shares * trade.price

    return render(request, 'core/history.html', { "trades": trades })

@login_required
def export_pdf(request):
    trades = models.Trade.objects.filter(user=request.user)

    for trade in trades:
        trade.total = trade.shares * trade.price

    template = loader.get_template('core/pdf.html')
    html = template.render({ "trades": trades })
    options = {
        "page-size": "Letter",
        "encoding": "UTF-8",
    }
    filename = "history.pdf"
    output = pdfkit.from_string(html, False, options)
    response = HttpResponse(output, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def export_csv(request):
    filename = "history.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    fields = ["User", "Date", "Type", "Symbol", "Shares", "Price", "Total"]
    writer.writerow(fields)
    trades = models.Trade.objects.filter(user=request.user)
    for trade in trades:
        total = trade.shares * trade.price
        writer.writerow([
            trade.user.username,
            trade.date,
            trade.trade_type,
            trade.stock.symbol,
            trade.shares,
            trade.price,
            total
        ])

    return response
