# Banked Coding Challenge

A test application for Banked's demo environment.

The test can be run with automatically configured Python environment by running:

```
docker compose up --build
```

For lower overhead, you can also set up your environment by running:

```
python -m pip install -r requirements.txt
pytest test_api.py
```