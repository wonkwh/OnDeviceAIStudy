// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "GradientDescent",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift", from: "0.25.0")
    ],
    targets: [
        .executableTarget(
            name: "GradientDescent",
            dependencies: [.product(name: "MLX", package: "mlx-swift")]
        )
    ]
)
