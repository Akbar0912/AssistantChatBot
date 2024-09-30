from flask import Flask, jsonify

app = Flask(__name__)

# Data JSON
data = [
    {
    "Date": "2013-11-07",
    "Open": 45.099998,
    "High": 50.09,
    "Low": 44.0,
    "Close": 44.900002,
    "Adj Close": 44.900002,
    "Volume": 117701670.0
  },
  {
    "Date": "2013-11-08",
    "Open": 45.93,
    "High": 46.939999,
    "Low": 40.685001,
    "Close": 41.650002,
    "Adj Close": 41.650002,
    "Volume": 27925307.0
  },
  {
    "Date": "2013-11-09",
    "Open": 45.93,
    "High": 46.939999,
    "Low": 40.685001,
    "Close": 41.650002,
    "Adj Close": 41.650002,
    "Volume": 27925307.0
  },
  {
    "Date": "2013-11-10",
    "Open": 45.93,
    "High": 46.939999,
    "Low": 40.685001,
    "Close": 41.650002,
    "Adj Close": 41.650002,
    "Volume": 27925307.0
  }
]

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
