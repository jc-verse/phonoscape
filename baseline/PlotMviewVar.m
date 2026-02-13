function [fh,ah] = PlotMviewVar(m, ht, cidx)
%PLOTMVIEWVAR  - temporal plot of mview variable
%
%	usage:  [fh,ah] = PlotMviewVar(m, ht, cidx)
%
% plots mview array-of-structs variable M optionally limited to HT [head,tail] (msecs)
%
% click and drag to adjust temporal zoom; double click restores full signal
%
% optional CIDX controls plotting of multidimensional components, a logical vector 
% with 1 for displayed dimensions (default [1 0 1])
%
% optionally returns created figure handle FH and axes handles AH

% mkt 11/23

if nargin < 1, help PlotMviewVar; return; end
if nargin < 2, ht = []; end
if nargin < 3 || isempty(cidx), cidx = logical([1 0 1]); else, cidx = logical(cidx); end

dim = [.1 .1 .82 .82];
nPanels = length(m)+1;
dy = dim(4)/(nPanels+1);		% spectrogram is double height

fh = figure('color','w');

% audio
s = m(1).SIGNAL;
asr = m(1).SRATE;
ns = length(s);
dur = 1000*ns/asr;
if isempty(ht)
	ht = [0 dur];
else
	hts = floor(ht/1000 * asr) + 1;
	if hts(1) < 1, ht(1) = 0; hts(1) = 1; end
	if hts(2) > ns, ht(2) = dur; hts(2) = length(s); end
	s = s(hts(1):hts(2));
	ns = length(s);
end
s0 = s;
ph = audioplayer(s0,asr);
t = linspace(ht(1), ht(2), ns)';
pos = [dim(1) dim(2)+dim(4)-dy dim(3) dy];
ah(1) = axes('position',pos);
plot(t,s)
set(ah(1),'xtick',[],'ytick',[],'xlim',ht)
ah(1).YLim = max(abs(ah(1).YLim))*2.5*[-.5 .5];

% spectrogram
pos(2) = pos(2) - 2*dy;
ah(2) = axes('position',[pos(1:3) 2*dy]);
sig = filter([1 -.98],1,s);
cut = min([6000,asr/2]);
wSize = round(6*asr/1000);
wSize = wSize + mod(wSize,2);
wSize2 = wSize / 2;
win = hanning(wSize);	
frameLen = 2^(ceil(log2(wSize))+2);
frameLen2 = frameLen / 2;
overlap = (1 * asr/1000);
z = sgram(sig);
[nBins,nFrames] = size(z);
f = linspace(0,cut,nBins);
t = linspace(ht(1),ht(2),nFrames);
ih = imagesc(t,f,z);
set(ah(2),'ydir','normal','xlim',t([1 end]),'xtick',[]);
colormap(gray(256).^6);
ylabel('Hz');

% get common scaling
r = 0;
idx = 1:8;
for k = 2 : length(m)
	s = m(k).SIGNAL;
	if size(s,2) == 1, continue; end
	r = max([r , range(s(:,idx(cidx)))]);
end
r = r*1.2/2;

% plot everything else
for k = 2 : length(m)
	s = m(k).SIGNAL;
	[ns,nd] = size(s);
	sr = m(k).SRATE;
	if nd > 1 
		s = s(:,idx(cidx));
		s = s - mean(s,'omitnan');
	end
	hts = floor(ht/1000 * sr) + 1;
	t = linspace(ht(1), ht(2), ns)';
	pos(2) = pos(2) - dy;
	ah(end+1) = axes('position',pos);
	plot(t,s,'linewidth',1.5)
	if nd > 1
		yl = mean(s(:),'omitnan')+[-r r]; 
	else
		yl = [min(s,[],'omitnan') max(s,[],'omitnan')] + range(s)*[-.05 .05];
	end
	set(ah(end),'xtick',[],'xlim',ht,'ylim',yl)
	axtoolbar(ah(end),{}); disableDefaultInteractivity(ah(end))		% disable toolstrip
	ylabel(m(k).NAME,'interpreter','none')
end

% make zoom axis overlaying everything
ah(end+1) = axes('position',dim,'tag','SCROLL','color','none','ytick',[],'xlim',ht,'xgrid','on','Interactions',zoomInteraction('Dimensions','x'));
title(inputname(1),'interpreter','none','fontweight','normal','fontsize',16)
xlabel('msecs')

% make squawk button
bh = uicontrol(fh,'style','pushbutton','string','Play','position',[10 10 50 15],'callback',@squawk);

% set up post-zoom callback to adjust all axes
zoom(ah(end),'on')
z = zoom(fh);
z.ActionPostCallback = @PostZoomCB;

% set up figure recreation CB to restore zoom
fh.CreateFcn = @CreateCB;

if nargout < 1, clear fh ; end

%% ----- CREATECB:  called on figure recreation to restore zoom
function CreateCB(~,~)
	h = findobj(ah,'tag','SCROLL');
	zoom(h,'on')
	z = zoom(fh);
	z.ActionPostCallback = @PostZoomCB;
end % CreateCB

%% ----- POSTZOOMDB:  called after zoom on overlay axis to update bounds on all axes
function PostZoomCB(~,~)
	h = findobj(ah,'tag','SCROLL');
	xl = h.XLim;
	h.YLim = [0 1];
	set(ah,'XLim',xl);
	delete(ph);
	hts = floor(xl*asr/1000)+1;
	ph = audioplayer(s0(hts(1):hts(2)),asr);
end % PostZoomCB

%% ----- SGRAM:  compute spectrogram
function z = sgram(sel)	
	ns = length(sel);
	nFrames = floor(ns/overlap);
	z = zeros(frameLen2, nFrames);
	sel = [zeros(wSize2,1) ; sel ; zeros(wSize,1)];
	sx = overlap/2;
	for fi = 1 : nFrames
		si = round(sx);
		p = abs(fft(win .* sel(si:si+wSize-1), frameLen));
		z(:,fi) = p(1:frameLen2);
		sx = sx + overlap;
	end;
	f = linspace(0, asr/2, frameLen2);
	if cut < asr/2
		f(find(f > cut)) = [];
		z = z(1:length(f),:);
	end
	z = filter(ones(3,1)/3, 1, abs(z), [], 2);
	z = uint8(255 * (1 - z / max(z,[],'all')));
end % sgram

%% ----- SQUAWK:  play sound pushbutton CB
function squawk(~,~)
	if isplaying(ph)
		stop(ph); 
	else 
		play(ph); 
	end
end % squawk

end % PlotMviewVar
