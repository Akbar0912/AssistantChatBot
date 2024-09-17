from flask import Flask, jsonify, request, abort

app = Flask(__name__)

# Dummy data for sales, revenue, and expenses
data = {
    "2024": {
        "Januari": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7000},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Februari": {
            "products": {
                "ProductA": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductB": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductC": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductD": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductE": {"sales": 140, "revenue": 14000, "expenses": 7000}
            }
        },
        "Maret": {
            "products": {
                "ProductA": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductB": {"sales": 170, "revenue": 17000, "expenses": 8500},
                "ProductC": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductD": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductE": {"sales": 150, "revenue": 15000, "expenses": 7500}
            }
        },
        "April": {
            "products": {
                "ProductA": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductB": {"sales": 180, "revenue": 18000, "expenses": 9000},
                "ProductC": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductD": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductE": {"sales": 160, "revenue": 16000, "expenses": 8000}
            }
        },
        "Mei": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juni": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 13000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 3000},
                "ProductD": {"sales": 140, "revenue": 19000, "expenses": 4000},
                "ProductE": {"sales": 170, "revenue": 11000, "expenses": 9500}
            }
        },
        "Juli": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 13000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 17000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 18000, "expenses": 8500}
            }
        },
        "Agustus": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8900}
            }
        },
        "September": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 130, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 120, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 180, "revenue": 17000, "expenses": 8500}
            }
        },
        "Oktober": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 130, "revenue": 14000, "expenses": 8500}
            }
        },
        "November": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 90, "revenue": 19000, "expenses": 10500},
                "ProductC": {"sales": 160, "revenue": 13000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 150, "revenue": 17000, "expenses": 8500}
            }
        },
        "Desember": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 4500},
                "ProductC": {"sales": 160, "revenue": 17000, "expenses": 8000},
                "ProductD": {"sales": 10, "revenue": 1400, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        }
    },
    "2023": {
        "Januari": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 50, "revenue": 15000, "expenses": 7000},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Februari": {
            "products": {
                "ProductA": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductB": {"sales": 160, "revenue": 13000, "expenses": 8000},
                "ProductC": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductD": {"sales": 110, "revenue": 14000, "expenses": 5500},
                "ProductE": {"sales": 140, "revenue": 14000, "expenses": 7000}
            }
        },
        "March": {
            "products": {
                "ProductA": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductB": {"sales": 170, "revenue": 17000, "expenses": 8500},
                "ProductC": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductD": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductE": {"sales": 150, "revenue": 15000, "expenses": 7500}
            }
        },
        "April": {
            "products": {
                "ProductA": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductB": {"sales": 180, "revenue": 18000, "expenses": 9000},
                "ProductC": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductD": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductE": {"sales": 160, "revenue": 16000, "expenses": 8000}
            }
        },
        "Mei": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juni": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juli": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Agustus": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "September": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 120, "revenue": 12000, "expenses": 6000}
            }
        },
        "Oktober": {
            "products": {
                "ProductA": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductB": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductC": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductD": {"sales": 70, "revenue": 7000, "expenses": 3500},
                "ProductE": {"sales": 100, "revenue": 10000, "expenses": 5000}
            }
        },
        "November": {
            "products": {
                "ProductA": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductC": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductD": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "December": {
            "products": {
                "ProductA": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductB": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductC": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductD": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductE": {"sales": 120, "revenue": 12000, "expenses": 6000}
            }
        }
    },
    "2022": {
        "Januari": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7000},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Februari": {
            "products": {
                "ProductA": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductB": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductC": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductD": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductE": {"sales": 140, "revenue": 14000, "expenses": 7000}
            }
        },
        "Maret": {
            "products": {
                "ProductA": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductB": {"sales": 170, "revenue": 17000, "expenses": 8500},
                "ProductC": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductD": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductE": {"sales": 150, "revenue": 15000, "expenses": 7500}
            }
        },
        "April": {
            "products": {
                "ProductA": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductB": {"sales": 180, "revenue": 18000, "expenses": 9000},
                "ProductC": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductD": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductE": {"sales": 160, "revenue": 16000, "expenses": 8000}
            }
        },
        "Mei": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juni": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juli": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Agustus": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "September": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 120, "revenue": 12000, "expenses": 6000}
            }
        },
        "Oktober": {
            "products": {
                "ProductA": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductB": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductC": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductD": {"sales": 70, "revenue": 7000, "expenses": 3500},
                "ProductE": {"sales": 100, "revenue": 10000, "expenses": 5000}
            }
        },
        "November": {
            "products": {
                "ProductA": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductC": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductD": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Desember": {
            "products": {
                "ProductA": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductB": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductC": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductD": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductE": {"sales": 120, "revenue": 12000, "expenses": 6000}
            }
        }
    },
    "2021": {
        "Januari": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7000},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Februari": {
            "products": {
                "ProductA": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductB": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductC": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductD": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductE": {"sales": 140, "revenue": 14000, "expenses": 7000}
            }
        },
        "Maret": {
            "products": {
                "ProductA": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductB": {"sales": 170, "revenue": 17000, "expenses": 8500},
                "ProductC": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductD": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductE": {"sales": 150, "revenue": 15000, "expenses": 7500}
            }
        },
        "April": {
            "products": {
                "ProductA": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductB": {"sales": 180, "revenue": 18000, "expenses": 9000},
                "ProductC": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductD": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductE": {"sales": 160, "revenue": 16000, "expenses": 8000}
            }
        },
        "Mei": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juni": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Juli": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "Agustus": {
            "products": {
                "ProductA": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductB": {"sales": 190, "revenue": 19000, "expenses": 9500},
                "ProductC": {"sales": 160, "revenue": 16000, "expenses": 8000},
                "ProductD": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductE": {"sales": 170, "revenue": 17000, "expenses": 8500}
            }
        },
        "September": {
            "products": {
                "ProductA": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductB": {"sales": 130, "revenue": 13000, "expenses": 6500},
                "ProductC": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductD": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductE": {"sales": 120, "revenue": 12000, "expenses": 6000}
            }
        },
        "Oktober": {
            "products": {
                "ProductA": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductB": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductC": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductD": {"sales": 70, "revenue": 7000, "expenses": 3500},
                "ProductE": {"sales": 100, "revenue": 10000, "expenses": 5000}
            }
        },
        "November": {
            "products": {
                "ProductA": {"sales": 110, "revenue": 11000, "expenses": 5500},
                "ProductB": {"sales": 150, "revenue": 15000, "expenses": 7500},
                "ProductC": {"sales": 120, "revenue": 12000, "expenses": 6000},
                "ProductD": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductE": {"sales": 130, "revenue": 13000, "expenses": 6500}
            }
        },
        "Desember": {
            "products": {
                "ProductA": {"sales": 90, "revenue": 9000, "expenses": 4500},
                "ProductB": {"sales": 140, "revenue": 14000, "expenses": 7000},
                "ProductC": {"sales": 100, "revenue": 10000, "expenses": 5000},
                "ProductD": {"sales": 80, "revenue": 8000, "expenses": 4000},
                "ProductE": {"sales": 100, "revenue": 12000, "expenses": 6000}
            }
        }
    }
}


@app.route('/api/sales_revenue', methods=['GET'])
def get_sales_revenue():
    """
    Retrieve sales, revenue, and expenses data based on year, month, and product.
    """
    year = request.args.get('year')
    month = request.args.get('month')
    product = request.args.get('product')

    # Validate the required parameter 'year'
    if not year:
        abort(400, description="Year parameter is required")

    year_data = data.get(year)
    if not year_data:
        abort(404, description="Data not found for the specified year")

    # If month is specified, filter by month
    if month:
        month_data = year_data.get(month)
        if not month_data:
            abort(404, description="Data not found for the specified month")

        # If product is specified, filter by product
        if product:
            product_data = month_data["products"].get(product)
            if not product_data:
                abort(404, description="Data not found for the specified product")
            
            return jsonify(product_data), 200
        
        return jsonify(month_data), 200
    
    # Return the entire year data if no month is specified
    return jsonify(year_data), 200

@app.route('/api/sales_summary', methods=['GET'])
def get_sales_summary():
    """
    Retrieve total sales, revenue, and expenses data based on year and month.
    """
    year = request.args.get('year')
    month = request.args.get('month')

    # Validate the required parameter 'year'
    if not year:
        abort(400, description="Year parameter is required")

    year_data = data.get(year)
    if not year_data:
        abort(404, description="Data not found for the specified year")

    # If month is specified, filter by month
    if month:
        month_data = year_data.get(month)
        if not month_data:
            abort(404, description="Data not found for the specified month")

        # Calculate totals for the month
        total_sales = sum(p['sales'] for p in month_data["products"].values())
        total_revenue = sum(p['revenue'] for p in month_data["products"].values())
        total_expenses = sum(p['expenses'] for p in month_data["products"].values())

        summary = {
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses
        }

        return jsonify(summary), 200
    
    # Calculate totals for the entire year if no month is specified
    total_sales = sum(
        sum(p['sales'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )
    total_revenue = sum(
        sum(p['revenue'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )
    total_expenses = sum(
        sum(p['expenses'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )

    summary = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses
    }

    return jsonify(summary), 200

@app.route('/api/sales_yearly', methods=['GET'])
def get_sales_yearly():
    """
    Retrieve total sales, revenue, and expenses data for the entire year.
    """
    year = request.args.get('year')

    # Validate the required parameter 'year'
    if not year:
        abort(400, description="Year parameter is required")

    year_data = data.get(year)
    if not year_data:
        abort(404, description="Data not found for the specified year")

    # Calculate totals for the entire year
    total_sales = sum(
        sum(p['sales'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )
    total_revenue = sum(
        sum(p['revenue'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )
    total_expenses = sum(
        sum(p['expenses'] for p in month_data["products"].values())
        for month_data in year_data.values()
    )

    summary = {
        "year": year,
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses
    }

    return jsonify(summary), 200


@app.errorhandler(400)
def bad_request(error):
    """
    Handle 400 Bad Request errors with a custom message.
    """
    return jsonify({"error": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors with a custom message.
    """
    return jsonify({"error": str(error)}), 404

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)
