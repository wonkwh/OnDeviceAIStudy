BIN := .build/xcode/Build/Products/Debug/GradientDescent

.PHONY: run build clean

run: build
	./$(BIN)

# swift build 는 metallib 를 만들지 않아 xcodebuild 사용
build:
	xcodebuild -scheme GradientDescent -destination 'platform=macOS,arch=arm64' -derivedDataPath .build/xcode build -quiet

clean:
	rm -rf .build
