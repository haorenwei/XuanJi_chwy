export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="relative h-10 w-10">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="absolute h-3 w-3 rounded-full bg-plum-400"
            style={{
              top: `${50 - 40 * Math.cos((i * 2 * Math.PI) / 5)}%`,
              left: `${50 + 40 * Math.sin((i * 2 * Math.PI) / 5)}%`,
              transform: 'translate(-50%, -50%)',
              animation: `pulse 1.2s ease-in-out ${i * 0.15}s infinite`,
              opacity: 0.3 + i * 0.15,
            }}
          />
        ))}
      </div>
    </div>
  )
}
