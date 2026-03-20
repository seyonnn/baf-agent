from flask import Flask, request

app = Flask(__name__)

@app.route("/exfil", methods=["POST"])
def exfil():
    data = request.get_data(as_text=True)
    print("\n[ExfilServer] Received exfil payload:")
    print(data[:1000])  # print first 1000 chars
    return "OK", 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
