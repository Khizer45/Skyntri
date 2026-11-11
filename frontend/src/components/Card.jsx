export default function Card({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag
      className={`rounded-xl border border-neutral-200 bg-white dark:border-white/10 dark:bg-panel-dark ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}
