from fastapi.testclient import TestClient

from app import DEVICE_KEY, app


JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def main():
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.post(f"/api/live/request/{DEVICE_KEY}").json()["live"] is True
    assert client.post("/api/live/request/chave-invalida").status_code == 401

    uploaded = client.post(
        "/api/live/frame",
        data={"device_key": DEVICE_KEY},
        files={"file": ("frame.jpg", JPEG, "image/jpeg")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["bytes"] == len(JPEG)

    state = client.get("/api/live/status", params={"device_key": DEVICE_KEY})
    assert state.status_code == 200
    assert state.json()["live"] is True
    assert state.json()["has_frame"] is True

    assert any(route.path == "/api/live/stream/{device_key}" for route in app.routes)
    assert client.get("/api/live/stream/chave-invalida").status_code == 401
    print("PASS: health, activation, status, frame upload and MJPEG route contract")


if __name__ == "__main__":
    main()
