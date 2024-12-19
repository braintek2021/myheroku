    import MetaTrader5 as mt5
    from flask import Flask, request, jsonify

    # Define the login credentials (passkey)
    PASSKEY = "Sreejm!@#$%"
    MT5_SERVER = "Exness-MT5Real6"
    MT5_LOGIN = 107796327
    MT5_PASSWORD = 'Sree87!@'
    # Global storage for position IDs
    position_store = {}

    # MT5 Initialization
    def initialize_mt5():
        if not mt5.initialize(login=MT5_LOGIN, server=MT5_SERVER, password=MT5_PASSWORD):
            print(f"MetaTrader 5 initialization failed: {mt5.last_error()}")
            return False
        print("MetaTrader 5 initialized successfully.")
        return True
        
    # Initialize MT5
    if not mt5.initialize(login=MT5_LOGIN, server=MT5_SERVER, password=MT5_PASSWORD):
        print(f"Initialization failed. Error: {mt5.last_error()}")
    else:
        print("MT5 initialized successfully")


    def place_buy_order(symbol, volume):
        point = mt5.symbol_info(symbol).point
        symbol_tick = mt5.symbol_info_tick(symbol)
        buyrequest = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": symbol_tick.ask,
            ##"sl": symbol_tick.ask - 1 * point,  # Stop loss 10 points away
            ##"tp": symbol_tick.ask + 1 * point,  # Take profit 10 points away
            "deviation": 1,  # Maximum price deviation in points
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Print the request for debugging
        print("Order request:", buyrequest)
        result = mt5.order_send(buyrequest)
        return result

    # Create a close request
    def place_sell_order(symbol, volume,position_id):    
        symbol_tick = mt5.symbol_info_tick(symbol)
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,  # Opposite of the buy order
            "price": symbol_tick.bid,
            "deviation": 1,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
            "position": position_id,  # Position ticket to close
            "comment": "Closing buy position"
        }
        print("Order request:", close_request)
        result2 = mt5.order_send(close_request)
        return result2
    
    app = Flask(__name__)
    @app.route('/webhook', methods=['POST'])
    def webhook():
        # Attempt to read JSON body
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400
    
        # Extract fields from the payload
        passkey = payload.get('passkey')
        symbol = payload.get('symbol')
        volume = float(payload.get('lotsize'))
        action = payload.get('action')
        
        print(f"Payload received: Symbol={symbol}, Volume={volume}, Action={action}")
    
        # Validate the passkey
        if passkey != PASSKEY:
            print("Invalid passkey provided.")
            return jsonify({"error": "Invalid passkey"}), 401
    
      # Handle Buy or Sell
        try:
            if action == "buy":
                if not initialize_mt5():
                    return jsonify({"error": "Failed to initialize MetaTrader 5"}), 500
                
                order_result = place_buy_order(symbol, volume)
                if order_result is None or order_result.retcode != mt5.TRADE_RETCODE_DONE:
                    error_message = order_result.comment if order_result else "Unknown error"
                    return jsonify({"error": f"Error placing buy order: {error_message}"}), 500
                
                # Save position ID for the symbol
                position_store[symbol] = order_result.order
                print(f"Buy order placed successfully for {symbol}. Order ID: {order_result.order}")
                response = {"success": True, "order_ticket": order_result.order}
            
            elif action == "sell":
                if not initialize_mt5():
                    return jsonify({"error": "Failed to initialize MetaTrader 5"}), 500
    
                # Retrieve position ID for the symbol
                position_id = position_store.get(symbol)
                if not position_id:
                    return jsonify({"error": f"No position ID found for symbol: {symbol}"}), 400
    
                order_result = place_sell_order(symbol, volume, position_id)
                if order_result is None or order_result.retcode != mt5.TRADE_RETCODE_DONE:
                    error_message = order_result.comment if order_result else "Unknown error"
                    return jsonify({"error": f"Error placing sell order: {error_message}"}), 500
                
                # Clear the stored position ID after selling
                del position_store[symbol]
                print(f"Sell order placed successfully for {symbol}. Order ID: {order_result.order}")
                response = {"success": True, "order_ticket": order_result.order}
            
            else:
                print("Invalid action received in payload.")
                return jsonify({"error": "Invalid action"}), 400
    
            print(f"Action '{action}' processed for {symbol}. Response: {response}")
            return jsonify(response)
        
        except Exception as e:
            print(f"Error processing request: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    if __name__ == '__main__':
        app.run(debug=True, use_reloader=False)

    

