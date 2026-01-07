from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello DevOps! 自动部署测试"


# git config --global http.proxy socks5://127.0.0.1:7897
# git config --global https.proxy socks5://127.0.0.1:7897



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)