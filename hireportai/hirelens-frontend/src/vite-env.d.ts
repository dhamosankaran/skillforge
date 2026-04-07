/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_GOOGLE_CLIENT_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// html2pdf.js has no official @types package
declare module 'html2pdf.js' {
  interface Html2PdfOptions {
    margin?: number | number[]
    filename?: string
    image?: { type?: string; quality?: number }
    html2canvas?: Record<string, unknown>
    jsPDF?: { unit?: string; format?: string; orientation?: string }
    pagebreak?: { mode?: string | string[] }
  }

  interface Html2PdfWorker {
    from(element: HTMLElement | string): Html2PdfWorker
    set(options: Html2PdfOptions): Html2PdfWorker
    save(): Promise<void>
    outputPdf(type: string): Promise<unknown>
  }

  function html2pdf(): Html2PdfWorker
  function html2pdf(element: HTMLElement, options?: Html2PdfOptions): Html2PdfWorker
  export = html2pdf
}
