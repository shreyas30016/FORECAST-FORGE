import * as React from "react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("bg-panel border border-border-subtle rounded-sm overflow-hidden flex flex-col", className)} {...props}>
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-4 py-3 border-b border-border-subtle bg-panel flex items-center justify-between", className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn("text-sm font-semibold tracking-tight text-text-primary uppercase flex items-center gap-2", className)} {...props}>
      {children}
    </h3>
  )
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-4 flex-1", className)} {...props}>
      {children}
    </div>
  )
}
