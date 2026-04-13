"use client";

import { useEffect, useRef } from "react";

export function InteractiveGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseLeave = () => {
      mouseRef.current = { x: -1000, y: -1000 };
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);

    const gridSize = 40;
    
    let animationFrameId: number;

    const render = () => {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, width, height);
      
      const isDark = false;
      ctx.strokeStyle = "rgba(0, 0, 0, 0.03)";
      ctx.lineWidth = 1;

      const pullDistance = 150;

      // Vertical lines
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        for (let y = 0; y < height; y += gridSize) {
          const dx = x - mouseRef.current.x;
          // adjusting y by canvas parent scroll offsets if the canvas is fixed? No, let's keep it relative to viewport 
          const dy = y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          let offsetX = 0;
          let offsetY = 0;

          if (dist < pullDistance) {
            const pull = (pullDistance - dist) / pullDistance;
            offsetX = -(dx * pull * 0.15);
            offsetY = -(dy * pull * 0.15);
          }

          if (y === 0) {
            ctx.moveTo(x + offsetX, y + offsetY);
          } else {
            ctx.lineTo(x + offsetX, y + offsetY);
          }
        }
        ctx.stroke();
      }

      // Horizontal lines
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        for (let x = 0; x < width; x += gridSize) {
          const dx = x - mouseRef.current.x;
          const dy = y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          let offsetX = 0;
          let offsetY = 0;

          if (dist < pullDistance) {
            const pull = (pullDistance - dist) / pullDistance;
            offsetX = -(dx * pull * 0.15);
            offsetY = -(dy * pull * 0.15);
          }

          if (x === 0) {
            ctx.moveTo(x + offsetX, y + offsetY);
          } else {
            ctx.lineTo(x + offsetX, y + offsetY);
          }
        }
        ctx.stroke();
      }

      // Draw subtle glow
      if (mouseRef.current.x > -1000) {
        const gradient = ctx.createRadialGradient(
          mouseRef.current.x, mouseRef.current.y, 0,
          mouseRef.current.x, mouseRef.current.y, 300
        );
        gradient.addColorStop(0, isDark ? "rgba(99, 102, 241, 0.15)" : "rgba(99, 102, 241, 0.08)");
        gradient.addColorStop(1, "rgba(99, 102, 241, 0)");
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      <canvas
        ref={canvasRef}
        className="absolute top-0 left-0 pointer-events-none w-full h-full"
      />
    </div>
  );
}
