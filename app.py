from flask import Flask, render_template, request

from src.recommendation import recommend_movies
from src.analytics import get_analytics

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    recommendations = []
    movie_name = ""

    analytics = get_analytics()          # 1. build analytics

    if request.method == "POST":
        movie_name = request.form.get("movie_name", "").strip()
        if movie_name:
            recommendations = recommend_movies(movie_name, num_recommendations=6)

    return render_template(
        "index.html",
        recommendations=recommendations,
        movie_name=movie_name,
        analytics=analytics              # 2. pass it to the template
    )


if __name__ == "__main__":
    app.run(debug=True)