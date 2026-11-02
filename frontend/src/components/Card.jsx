export default function Card({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag
      className={`rounded-2xl border border-neutral-200/80 bg-white shadow-card dark:border-white/5 dark:bg-panel-dark ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}
