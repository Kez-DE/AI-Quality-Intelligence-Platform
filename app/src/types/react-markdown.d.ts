declare module 'react-markdown' {
  import type { ComponentType, ReactNode } from 'react';

  export interface Options {
    children?: string | null | undefined;
    className?: string;
    components?: Record<string, ComponentType<any>>;
    [key: string]: any;
  }

  declare const ReactMarkdown: ComponentType<Options>;
  export default ReactMarkdown;
}
