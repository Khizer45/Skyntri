import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Markdown from the assistant and clinic posts. Raw HTML in the text is
// never rendered (react-markdown's default), links open in a new tab and
// images are dropped: only the server may attach images.
const components = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer nofollow" />,
  img: () => null,
  table: ({ node, ...props }) => (
    <div className="table-wrap">
      <table {...props} />
    </div>
  ),
}

export default function Markdown({ children, className = '' }) {
  return (
    <div className={`prose-chat ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children || ''}
      </ReactMarkdown>
    </div>
  )
}
