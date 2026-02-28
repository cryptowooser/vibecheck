import uvicorn


def main() -> None:
    uvicorn.run(
        "vibecheck.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=7870,
    )


if __name__ == "__main__":
    main()
