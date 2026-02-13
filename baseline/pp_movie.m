function ppState = pp_movie(ppState, action, varargin)
%PP_MOVIE  - MVIEW procedure for coplotting a synchronized movie
%
%	varargin{1} movie name (required)
%	varargin{2} offset of movie relative to mview data (ms; default 0)
%	             a positive value means movie begins after mview data; negative before
%	varargin{3} magnification factor (default 1)
%
% examples
% mview('foo','pproc',{'pp_movie','foo.mov'})
% mview('foo','pproc',{'pp_movie',{'foo.mov',3000,.5}})

% mkt 05/18 

%	branch by action (2nd argument)

switch upper(action),
		
%-----------------------------------------------------------------------------
% CLOSE:  delete plot

	case 'CLOSE',
		fh = ppState.FH;
		if ishandle(fh), delete(fh); end;
		
	
%-----------------------------------------------------------------------------
% INIT:  initialize plot
%
%	ppState set to mview state copy
%	varargin{1} movie name (required)
%	varargin{2} offset of movie relative to mview data (ms; default 0)
%	varargin{3} magnification factor (default 1)
%
% 	returns updated ppState

	case 'INIT',
		switch length(varargin),
			case 3, fName = varargin{1}; offset = varargin{2}; mag = varargin{3};
			case 2, fName = varargin{1}; offset = varargin{2}; mag = 1;
			case 1, fName = varargin{1}; offset = 0; mag = 1;
			otherwise, error('pp_movie requires at least one parameter (filename)');
		end;
		if isempty(offset), offset = 0; end;
		if isempty(mag), mag = 1; end;
					
% keep figure on top
		fh = figure('name',fName, 'menuBar','none', 'units','pixels', 'resize','off', 'tag','MVIEW');
		drawnow;
% 		warning('off','MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
% 		warning('off','MATLAB:ui:javaframe:PropertyToBeRemoved');
% 		jf = get(handle(fh),'JavaFrame');
% 		warning('on','MATLAB:ui:javaframe:PropertyToBeRemoved');
% 		warning('on','MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
% 		jf.fHG2Client.getWindow.setAlwaysOnTop(true);
		
% open the movie
		mh = VideoReader(fName);

% use first image to size display
		offs = ppState.CURSOR - offset;
		[img,frame] = GetMovieFrame(mh,offs,mag);
		[r,c] = size(img);
		pos = get(fh,'position');
		set(fh, 'position',[pos(1) , pos(2)+pos(4)-r , c, r], 'colormap',gray(256));
		ih = imagesc(img);
		clim = get(gca,'clim');
		set(gca, 'position',[0 0 1 1], 'xtick',[],'ytick',[]);

% display frame number
		th = text(50,80,sprintf('%04d',frame),'fontsize',18,'color','w');

% save data
		ppState = struct('FH',fh, 'IH',ih, 'MH',mh, 'TH',th, 'OFFSET',offset, 'MAG',mag, 'MVIEW',ppState.FH);
		
		
%-----------------------------------------------------------------------------
% UDBNDS:  update the plot based on current selection
%
%	varargin{1} set to state.HEAD
%	varargin{2} set to state.TAIL

	case 'UDBNDS',
		;
	
%-----------------------------------------------------------------------------
% UDCURS:  update the plot based on current cursor location
%
%	varargin{1} set to state.CURSOR

	case 'UDCURS',
		if ~ishandle(ppState.FH), return; end;
		[img,frame] = GetMovieFrame(ppState.MH,varargin{1}-ppState.OFFSET,ppState.MAG);
		set(ppState.IH,'cdata',img);
		set(ppState.TH,'string',sprintf('%04d',frame));
		drawnow;
		
%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['PP_MOVIE:  unrecognized action (', action, ')']);
	
end;


%=============================================================================
% GETMOVIEFRAME  - get frame from open video object
%
%	usage:  [img,frame] = GetMovieFrame(mh, offs, mag)
%
% returns IMG at OFFS (ms) scaled by MAG in single-plane uint8 format
% and 1-based movie FRAME number corresponding to OFFS
%
% offsets outside of available data return an empty image

function [img,frame] = GetMovieFrame(mh, offs, mag)

frame = floor(offs/1000 * mh.FrameRate) + 1;

if offs < 0 || offs/1000 > mh.Duration,
	OOR = 1;
	offs = 0;
else,
	OOR = 0;
end;
mh.CurrentTime = offs/1000;
img = mean(readFrame(mh),3);

% filter when scale < 1 to avoid aliasing
if mag < 1,
	[ih,iw] = size(img);
	mih = floor(ih*mag); miw = floor(iw*mag);
	h = fir1(10, mih/ih)' * fir1(10, miw/iw);
	img = filter2(h, img);
end;

% build interpolation indices
if mag ~= 1,
	[ih,iw] = size(img);
	mih = floor(ih*mag);
	miw = floor(iw*mag);
	[x,y] = meshgrid(1:(iw-1)/(miw-1):iw, 1:(ih-1)/(mih-1):ih);

% interpolate
	img = uint8(interp2(img, x, y, 'cubic'));
else,
	img = uint8(img);
end;

if OOR, img = img * uint8(0); end;
