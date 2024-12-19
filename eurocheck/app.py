from chalice import Chalice, BadRequestError
import MetaTrader5 as mt5

app = Chalice(app_name='tradingview-webhook-eurobuy')

# Define the login credentials (passkey)
PASSKEY = "Sreejm!@#$%"
MT5_SERVER = "Exness-MT5Real6"
MT5_LOGIN = 107796327
MT5_PASSWORD = 'Sree87!@'

# MT5 Initialization
def initialize_mt5():
    if not mt5.initialize(login=MT5_LOGIN, server=MT5_SERVER, password=MT5_PASSWORD):
        print(f"MetaTrader 5 initialization failed: {mt5.last_error()}")
        return False
    print("MetaTrader 5 initialized successfully.")
    return True

# Buy function
def place_buy_order(symbol, volume):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found.")
        return None
    
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select symbol {symbol}.")
            return None

    point = symbol_info.point
    symbol_tick = mt5.symbol_info_tick(symbol)
    
    buy_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": symbol_tick.ask,
        "deviation": 10,  # Maximum price deviation in points
        "comment": "Python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print("Order request:", buy_request)
    result = mt5.order_send(buy_request)
    return result

# Sell function
def place_sell_order(symbol, volume, position_id):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found.")
        return None

    symbol_tick = mt5.symbol_info_tick(symbol)

    sell_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL,
        "price": symbol_tick.bid,
        "deviation": 10,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "position": position_id,  # Position ticket to close
        "comment": "Closing buy position",
    }
    
    print("Close order request:", sell_request)
    result = mt5.order_send(sell_request)
    return result

@app.route('/webhook', methods=['POST'])
def webhook():
    request = app.current_request

    # Attempt to read JSON body
    try:
        payload = request.json_body
        if not payload:
            raise BadRequestError("Invalid or missing JSON payload")
    except Exception:
        raise BadRequestError("Invalid or missing JSON payload")

    # Extract fields from the payload
    passkey = payload.get('passkey')
    symbol = payload.get('symbol')
    volume = float(payload.get('lotsize'))
    action = payload.get('action')
    
    print(f"Payload received: Symbol={symbol}, Volume={volume}, Action={action}")

    # Validate the passkey
    if passkey != PASSKEY:
        print("Invalid passkey provided.")
        return {"error": "Invalid passkey"}, 401

    # Initialize MT5
    if not initialize_mt5():
        return {"error": "Failed to initialize MetaTrader 5"}, 500

    # Handle Buy or Sell
    try:
        if action == "buy":
            order_result = place_buy_order(symbol, volume)
            if order_result is None:
                return {"error": "Failed to place buy order"}, 500
            if order_result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"error": f"Error placing buy order: {order_result.retcode}, {order_result.comment}"}, 500
            print("Buy order placed successfully.", order_result)
            response = {"success": True, "order_ticket": order_result.order}
        elif action == "sell":
            position_id = payload.get('position_id')
            if not position_id:
                return {"error": "Missing position_id for sell action"}, 400
            
            order_result = place_sell_order(symbol, volume, position_id)
            if order_result is None:
                return {"error": "Failed to place sell order"}, 500
            if order_result.retcode != mt5.TRADE_RETCODE_DONE:
                return {"error": f"Error placing sell order: {order_result.retcode}, {order_result.comment}"}, 500
            print("Sell order placed successfully.", order_result)
            response = {"success": True, "order_ticket": order_result.order}
        else:
            print("Invalid action received in payload.")
            return {"error": "Invalid action"}, 400

        print(f"Action '{action}' processed for {symbol}. Response: {response}")
        return response
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {"error": str(e)}, 500
