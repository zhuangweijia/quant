export interface ResponseBase<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface PageResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
