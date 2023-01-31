import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]
    # Get the information of the user Portfolio
    transactions_db = db.execute("SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
    user_cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    user_cash = user_cash_db[0]["cash"]
    for row in transactions_db:
        row['name'] = lookup(row['symbol'])['name']
        row['price'] = round(lookup(row['symbol'])['price'], 2)

    # Send the user to the index page
    return render_template("index.html", transactions=transactions_db, cash = user_cash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("buy.html")
    # User reached route via POST (as by submitting a form via POST)
    else:
        # Create Var to store the values
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if not symbol:
            return apology("Please type a Symbol")
        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Please type a valid Symbol")

    # Check the transaction value and store it in the Var
        transaction_value = shares * stock["price"]

        user_id = session["user_id"]
    # Check how much cash the user has and store it in the Var
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
    # Real Cash from the user
        user_cash = user_cash_db[0]["cash"]
    # Check if the user has enough cash to buy the share
        if transaction_value > user_cash:
            return apology("Insuficient funds for this transaction")
    # Current balance of the user
        user_balance = user_cash - transaction_value
    # Update the balance of the user
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_balance, user_id)
    # Get the exact time the user is buying shares
        date = datetime.datetime.now()
    # UPDATE table_name SET column1 = value1, column2 = value2, ... WHERE condition;
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",user_id, stock["symbol"], shares, stock["price"], date)
    # Send the user to the homepage
        flash(usd(transaction_value))
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions_db = db.execute("SELECT * FROM transactions WHERE user_id = :id", id=user_id)
    return render_template("history.html", transactions=transactions_db)




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

        # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    #  User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("quote.html")

    # User reached route via POST (as by submitting a form via POST)
    else:
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Please type a Symbol")
    # Create a var to save the symbol
        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Please type a valid Symbol")

        return render_template("quoted.html", name=stock["name"], price=stock["price"], symbol=stock["symbol"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("register.html")
     # User reached route via POST (as by submitting a form via POST)
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
    # If username is blank
    if not username:
        return apology("Please type an username")
    # If password is blank
    if not password:
        return apology("Please type a password")
    # If confirmation password is blank
    if not confirmation:
        return apology("Please Repeat your password")
    # If passwords don't match
    if password != confirmation:
        return apology("Passwords don't match")
    # Create a var to store/hide the password
    hash = generate_password_hash(password)
    # insert new user in the db
    try:
        new_user = db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", username, hash)
    except:
        return apology("Choose a different username")

    # Send the user to homepage
    session["user_id"] = new_user
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
       user_id = session["user_id"]
       user_symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = :id Group BY symbol HAVING SUM (shares) > 0", id=user_id)
       return render_template("sell.html", symbols=[row["symbol"] for row in user_symbols])
    # User reached route via POST (as by submitting a form via POST)
    # Create Var to store the values
    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if not symbol:
            return apology("Please type a Symbol")
        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Please type a valid Symbol")

        if shares < 0:
            return apology("Please introduce positive number of shares")


    # Check the transaction value and store it in the Var
        transaction_value = shares * stock["price"]

        user_id = session["user_id"]
    # Check how much cash the user has and store it in the Var
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
    # Real Cash from the user
        user_cash = user_cash_db[0]["cash"]

    # Update user cash
        user_balance = user_cash + transaction_value
    # Update the balance of the user
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_balance, user_id)
    # Check if user has the quantity of shares
        user_shares = db.execute("SELECT SUM(shares) AS shares FROM transactions WHERE user_id=? AND symbol=?", user_id, symbol)
        user_shares_r = user_shares[0]["shares"]

        if shares > user_shares_r:
            return apology("You don't have enough shares")
    # Get the exact time the user is buying shares
        date = datetime.datetime.now()
    # UPDATE table_name SET column1 = value1, column2 = value2, ... WHERE condition;
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",
                    user_id, stock["symbol"], (-1)*shares, stock["price"], date)
    # Send the user to the homepage
        flash(usd(transaction_value))
        return redirect("/")
